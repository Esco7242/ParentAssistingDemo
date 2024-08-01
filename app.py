import logging
import streamlit as st
import requests
from xml.etree import ElementTree
from openai import OpenAI, AssistantEventHandler
import os
from streamlit_lottie import st_lottie_spinner
import json
from typing_extensions import override
from datetime import datetime
import time
from streamlit.components.v1 import html  # Add this import

# Custom CSS for layout and spacing
st.markdown("""
    <style>
        .main-title {
            margin-top: 40px;
            margin-bottom: 20px;
            font-size: 30px;
            line-height: 1.2;
            white-space: nowrap;
        }
        .input-area, .api-selection, .response-section {
            margin-top: 20px;
            margin-bottom: 20px;
            padding: 20px;
            border-radius: 10px;
            background-color: #f9f9f9;
        }
        .custom-button {
            margin-top: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# Custom CSS for color scheme and typography
st.markdown("""
    <style>
        body {
            background-color: #f0f2f6;
        }
        .main-title {
            color: #4CAF50;
        }
        .input-area, .api-selection, .response-section {
            background-color: #ffffff;
            border: 1px solid #ddd;
        }
        .custom-button {
            background-color: #4CAF50;
            color: white;
        }
        .custom-button:hover {
            background-color: #45a049;
        }
        .search-box {
            width: 100%;
            font-size: 18px;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #ccc;
            margin-bottom: 20px;
        }
        .options-container {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .section-title {
            font-size: 1em;
            font-weight: normal;
            color: #333;
        }
        .options-container label {
            font-size: 1em;
            color: #333;
        }
    </style>
""", unsafe_allow_html=True)

# Additional CSS for responsive design
st.markdown("""
    <style>
        @media screen and (max-width: 600px) {
            .main-title {
                font-size: 25px;
            }
        }
        @media screen and (min-width: 601px) {
            .main-title {
                font-size: 30px;
            }
        }
    </style>
""", unsafe_allow_html=True)

OPENAI_API_KEY = st.secrets["openai"]["api_key"]
NCBI_BASE_URL = st.secrets["ncbi"]["base_url"]

assert OPENAI_API_KEY, "OPENAI_API_KEY is not set"
assert NCBI_BASE_URL, "NCBI_BASE_URL is not set"

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("log_demo.txt"), logging.StreamHandler()])
logger = logging.getLogger(__name__)

logger.info("Environment variables loaded successfully")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)
logger.info("OpenAI client initialized")

class EventHandler(AssistantEventHandler):
    def __init__(self, placeholder=None):
        super().__init__()
        self.text_accumulated = ''
        self.placeholder = placeholder
        self.first_chunk = True
        logger.info("EventHandler initialized")

    @override
    def on_text_created(self, text):
        logger.info(f"Text created: {text.value}")

    @override
    def on_text_delta(self, delta, snapshot):
        if self.first_chunk:
            self.text_accumulated = delta.value
            self.first_chunk = False
        else:
            self.text_accumulated += delta.value
        if self.placeholder:
            self.placeholder.markdown(self.text_accumulated)

    @override
    def on_text_done(self, text):
        logger.info(f"Text done: {text.value}")

def create_assistant():
    assistant = client.beta.assistants.create(
        name="Research Assistant",
        instructions="""
        You are a research assistant. Accuracy is of the utmost importance
        """,
        model="gpt-4o-mini"
    )
    logger.info(f"Assistant created: {assistant.id}")
    return assistant
    
def run_assistant(thread_id, assistant_id, task, placeholder=None):
    handler = EventHandler(placeholder)
    logger.info(f"Running assistant {assistant_id} for thread {thread_id} with task: {task}")
    with client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant_id,
        event_handler=handler,
        model="gpt-4o-mini",
        temperature=0.3,
    ) as stream:
        stream.until_done()
    logger.info(f"Assistant run completed. Accumulated text: {handler.text_accumulated[:50]}...")
    return handler.text_accumulated

def create_thread():
    thread = client.beta.threads.create()
    logger.info(f"Thread created: {thread.id}")
    return thread

def add_message_to_thread(thread_id, content, role="user"):
    runs = client.beta.threads.runs.list(thread_id=thread_id)
    
    active_run = next((run for run in runs if run.status in ["queued", "in_progress"]), None)
    
    while active_run:
        logger.info(f"Waiting for active run to complete for thread {thread_id}")
        time.sleep(1)
        runs = client.beta.threads.runs.list(thread_id=thread_id)
        active_run = next((run for run in runs if run.status in ["queued", "in_progress"]), None)
    
    message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role=role,
        content=content
    )
    logger.info(f"Message added to thread {thread_id}: {content[:50]}...")
    return message

def load_lottiefile(filepath: str):
    try:
        with open(filepath, "r") as f:
            logger.info(f"Loading Lottie file from {filepath}")
            return json.load(f)
    except FileNotFoundError:
        st.error(f"File {filepath} not found.")
        logger.error(f"File {filepath} not found.")
        return None

loading_animation = load_lottiefile("animation.json")

st.markdown("""
    <style>
        @media screen and (max-width: 600px) {
            .main-title {
                font-size: 36px;
            }
        }
        @media screen and (min-width: 601px) {
            .main-title {
                font-size: 40px;
            }
        }
        .main-title {
            font-family: 'Courier New', monospace;
            color: #4CAF50;
            text-align: center;
            font-weight: bold;
            background: linear-gradient(to right, blue, pink);
            -webkit-background-clip: text;
            color: transparent;
            margin-top: 40px;
        }
        .disclaimer {
            font-size: 14px;
            color: #888888;
            margin-bottom: 20px;
            text-align: center;
        }
        .input-area {
            font-family: 'Courier New', monospace;
            margin-top: 22px;
        }
        .custom-button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
        }
        .custom-button:hover {
            background-color: #45a049;
        }
        .article-card {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
        }
        .article-title {
            font-size: 1.2em;
            color: #333;
            font-weight: bold;
        }
        .article-authors {
            color: #777;
        }
        .article-details {
            margin-top: 10px;
            font-size: 0.9em;
            color: #555;
        }
        .search-box {
            width: 100%;
            font-size: 18px;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #ccc;
            margin-bottom: 20px;
        }
        .options-container {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# Title
st.markdown("<h1 class='main-title'>Parenting Assistance Demo</h1>", unsafe_allow_html=True)

# User Input Section
if 'enter_pressed' not in st.session_state:
    st.session_state.enter_pressed = False

def on_enter_pressed():
    st.session_state.enter_pressed = True

user_input = st.text_input(
    "",
    key="user_input",
    placeholder="Enter your research question here...",
    label_visibility="collapsed",
    max_chars=200,
    on_change=on_enter_pressed
)

generate = st.button("Generate", key='generate_button', help="Click to generate a response", use_container_width=True)

response_placeholder = st.empty()

# Add this JavaScript to capture the Enter key press
js_code = """
<script>
document.addEventListener('keydown', function(e) {
    if (e.key == 'Enter') {
        setTimeout(function() {
            document.getElementsByTagName('button')[0].click();
        }, 0);
    }
});
</script>
"""
html(js_code, height=0)

# Options Section with Expander
st.markdown("<div class='options-container'>", unsafe_allow_html=True)

with st.expander("Change Complexity to Doctor level:", expanded=False):
    length_selection = st.radio(
        "",
        ("Parent", "Doctor/Researcher"),
        index=0,
        key="length_radio"
    )

st.markdown("</div>", unsafe_allow_html=True)

# Initialize conversation history and user_input in session state
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = [{"role": "system", "content": "You are a helpful assistant."}]
    logger.info("Conversation history initialized")
    
# Setup assistant and thread outside the button click logic
if 'assistant' not in st.session_state:
    st.session_state.assistant = create_assistant()
if 'thread' not in st.session_state:
    st.session_state.thread = create_thread()

def optimize_question(thread_id, question):
    task = (
        f"Transform the question: {question} to be a cohesive yet extremely simple question with a few simple, but extremely relevant keywords. Only, I REPEAT: ONLY, output the optimized revised question."
    )
    add_message_to_thread(thread_id, task)
    response_text = run_assistant(thread_id, st.session_state.assistant.id, task)
    if response_text:
        optimized_question = response_text.strip()
        logger.info(f"Optimized question: {optimized_question}")
        return optimized_question
    else:
        logger.warning("No optimized question generated")
        return question

def extract_keywords(thread_id, question):
    optimized_question = optimize_question(thread_id, question)
    task = (
        f"Extract the most essential academic keywords from the following research question. Choose the most relevant 4 keywords max. The choices of words will be going into an API call to search PubMed. Make sure the keywords are the most essential keywords for doing a search on PubMeds API"
        f"Research Question: {optimized_question}. Output keywords separated by commas, ranked from most relevant to least relevant."
    )
    add_message_to_thread(thread_id, task)
    response_text = run_assistant(thread_id, st.session_state.assistant.id, task)
    if response_text:
        keywords = response_text.split(',')
        clean_keywords = [keyword.strip() for keyword in keywords]
        logger.info(f"Extracted keywords: {clean_keywords}")
        return clean_keywords
    else:
        logger.warning("No keywords extracted")
        return []

def generate_response(question, length, context, placeholder):
    if not question.strip():
        st.error("Please enter a valid research question.")
        return "", ""
    
    if not context.strip():
        logger.warning("No articles found. Generating response without context.")
        context = "No specific articles found. Please provide a general response based on your knowledge."
    
    def generate_prompt(optimized_question, length, context):
        # Split the context into individual articles
        articles = context.split("\n\n")
        
        def safe_sort_key(article):
            try:
                # Try to find the published date
                published_parts = article.split("Published: ")
                if len(published_parts) > 1:
                    date_part = published_parts[1].split("\n")[0]
                    # Try to parse the date, default to '0' if it fails
                    return date_part if date_part.isdigit() else '0'
                else:
                    return '0'  # Default to '0' if "Published: " is not found
            except Exception:
                return '0'  # Default to '0' for any other error
        
        # Sort articles by publication year, with error handling
        sorted_articles = sorted(articles, key=safe_sort_key, reverse=True)
        
        # Join the sorted articles back into a single string
        sorted_context = "\n\n".join(sorted_articles)
        
        prompts = {
        "Parent": f"""
        You are a helpful brilliant assistant serving low income families. You are a GPT-4o model with access to major journals. Your task is to answer simple parenting questions accurately and clearly for parents. Deliver a simple response to '{optimized_question}', using the context below. 

        IMPORTANT: You MUST cite information from EACH provided article that is relevant to the question. Prioritize information from the most recent studies. The articles are provided in order from newest to oldest. Give more weight to the findings from the newer studies, but don't ignore older studies if they provide crucial information.

        Cite the studies' authors and years immediately after presenting facts. Use the format (Author Year) for citations. Make sure you consider and cite at least one fact from each relevant article abstract provided in the context, with a focus on the most recent ones.

        Use natural language that is easy to understand. Don't use scientific terms. Don't use numbered lists. All answers should be simple. Assume an IQ of 120. Aim for approximately 150 words, focusing on practical advice that parents can easily apply. Synthesize information from the most relevant and recent research. Ensure your answer is grounded in solid research while being accessible. Remember: simple language, I repeat: simple language.

        Prioritize articles by published date and ensure all articles are taken into account before answering the question. This is of the utmost importance. 
        
        Context (ordered from newest to oldest):
        {sorted_context}

        Before outputting your response, verify that you've cited each relevant article provided in the context, with emphasis on the most recent ones. Your response MUST include at least one citation from each article that is relevant to the question. If an article is not relevant to the specific question, explain briefly why you didn't include it.

        After your main response, provide a brief summary of how many articles you cited and why you may not have cited certain articles (if any).

        Remember: DO NOT USE SCIENTIFIC JARGON

        Before outputting, validate that you answered the user's question with a direct and clear response to THEIR question. Answering the question {optimized_question} is the most important aspect of this app.[IMPORTANT]!. For example, if the user asks about baby formula, DO NOT mention breastfeeding. That's not what they are asking about.
        
        IMPORTANT: You MUST cite information from EACH provided article that is relevant to the question. The articles are provided in order of relevance to the question. Give more weight to the findings from the more relevant studies, but don't ignore less relevant studies if they provide crucial information.
        """,
        "Doctor/Researcher": f"""
        You are Brilliance, a GPT-4o model with access to major journals. Your sole task is to accurately, and I repeat: accurately, answer the user's question with empirical data. You will emulate a wide beam search when considering your choice of words. This is the most important thing to remember. Deliver a brilliant and detailed, scientifically validated response to '{optimized_question}', using the context below. 

        IMPORTANT: Prioritize information from the most recent studies. The articles are provided in order from newest to oldest. Give more weight to the findings from the newer studies, but don't ignore older studies if they provide crucial information or historical context.

        Cite the studies' authors and years immediately after presenting facts. Clarify the mechanisms of action when discussing medicine. Craft the answer in natural, flowing language, avoiding numbered lists or subtopic breakdowns. Synthesize information from recent and cutting-edge research, emphasizing groundbreaking discoveries and their practical implications. Highlight innovative theories or advancements that could revolutionize our understanding, focusing on the unique aspects of the research question within the latest context. 

        Reference the original question frequently, aiming for approximately 1000 words. Include accurate data, values, variables, and relevant names or places. Be specific, avoid generalizations, and eschew repetitive phrasing. Aim to leave the reader with a profound understanding, using a natural academic tone suitable for an audience with an IQ of 200. Extrapolate and synthesize groundbreaking insights. 

        Ensure the question is completely and accurately answered, considering the data from the context provided, with emphasis on the most recent findings. Make sure your results show groundbreaking findings. Remember to synthesize responses with citations in parentheses. Just use relevant author names and year in the prompt.
        Context (ordered from newest to oldest):
        {sorted_context}
        Before outputting your response, verify that you've cited each relevant article provided in the context, with emphasis on the most recent ones. Only cite articles that are directly relevant to answering the user's question. If an article is not relevant to the specific question, you do not need to cite it.

        Prioritize articles by published date and ensure all articles are taken into account before answering the question. This is of the utmost importance. 
        
        IMPORTANT: Prioritize information from the most relevant studies. The articles are provided in order of relevance to the question. Give more weight to the findings from the more relevant studies, but don't ignore less relevant studies if they provide crucial information or historical context.
        """
        }
        return prompts.get(length, prompts["Parent"])
    
    optimized_question = optimize_question(st.session_state.thread.id, question)
    prompt = generate_prompt(optimized_question, length, context)

    add_message_to_thread(st.session_state.thread.id, prompt)
    
    handler = EventHandler(placeholder)
    with client.beta.threads.runs.stream(
        thread_id=st.session_state.thread.id,
        assistant_id=st.session_state.assistant.id,
        event_handler=handler,
    ) as stream:
        stream.until_done()
    
    response = handler.text_accumulated
    logger.info(f"Generated response: {response[:50]}...")

    # Generate text message version
    text_message_prompt = f"""
    Convert the following response into a concise text message of 450 characters or less. 
    Remove all citations and speak in simple language. Make it casual and friendly, as if texting a friend. Use 2 emojis at the end of the text message. Always, I repeat: ALWAYS say this at the end: This is not medical advice, this is research. Always check with your doctor before making any choices based on this response.
    Don't use medical jargon.
    Original response:
    {response}
    """
    add_message_to_thread(st.session_state.thread.id, text_message_prompt)
    
    text_message_handler = EventHandler()
    with client.beta.threads.runs.stream(
        thread_id=st.session_state.thread.id,
        assistant_id=st.session_state.assistant.id,
        event_handler=text_message_handler,
    ) as stream:
        stream.until_done()
    
    text_message = text_message_handler.text_accumulated
    logger.info(f"Generated text message: {text_message[:50]}...")
    
    return response, text_message

def search_ncbi(keywords, num_results):
    if not keywords:
        logger.warning("No keywords provided for NCBI search.")
        return []

    query = '+'.join(keywords)
    articles = []

    # Search for the most relevant results
    relevant_url = f"{NCBI_BASE_URL}esearch.fcgi?db=pubmed&term={query}&retmode=json&retmax={num_results}&sort=relevance"
    relevant_response = requests.get(relevant_url)
    logger.info(f"NCBI relevant search API response status: {relevant_response.status_code}")

    if relevant_response.status_code == 200:
        relevant_id_list = relevant_response.json().get('esearchresult', {}).get('idlist', [])
        articles = fetch_article_details(relevant_id_list)

    if not articles:
        # If no results, try a more general search
        general_query = '+OR+'.join(keywords)
        general_url = f"{NCBI_BASE_URL}esearch.fcgi?db=pubmed&term={general_query}&retmode=json&retmax={num_results}&sort=relevance"
        general_response = requests.get(general_url)
        logger.info(f"NCBI general search API response status: {general_response.status_code}")

        if general_response.status_code == 200:
            general_id_list = general_response.json().get('esearchresult', {}).get('idlist', [])
            articles = fetch_article_details(general_id_list)

    logger.info(f"NCBI search results: {len(articles)} articles found")
    return articles

def fetch_article_details(id_list):
    if not id_list:
        return []

    fetch_url = f"{NCBI_BASE_URL}efetch.fcgi?db=pubmed&id={','.join(id_list)}&retmode=xml"
    fetch_response = requests.get(fetch_url)
    logger.info(f"NCBI fetch API response status: {fetch_response.status_code}")

    if fetch_response.status_code != 200:
        logger.error(f"Error fetching detailed data from NCBI: {fetch_response.text}")
        return []

    articles = []
    root = ElementTree.fromstring(fetch_response.content)
    for article in root.findall('.//PubmedArticle'):
        title = article.find('.//ArticleTitle')
        abstract = article.find('.//AbstractText')
        pubmed_id = article.find('.//ArticleId[@IdType="pubmed"]')
        pub_date = article.find('.//PubDate/Year')
        authors = [
            author.find('LastName').text + " " + author.find('ForeName').text
            for author in article.findall('.//Author')
            if author.find('LastName') is not None and author.find('ForeName') is not None
        ]
        articles.append({
            'title': title.text if title is not None else 'No title',
            'abstract': abstract.text if abstract is not None else 'No abstract',
            'id': pubmed_id.text if pubmed_id is not None else 'No ID',
            'published': pub_date.text if pub_date is not None else 'No date',
            'authors': authors,
            'source': 'PubMed',
            'url': f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id.text}/" if pubmed_id is not None else 'No URL'
        })

    return articles

def display_article_card(article, is_dark_mode=False):
    abstract = article.get('abstract', 'No abstract')
    if not isinstance(abstract, str):
        abstract = 'No abstract'
    
    abstract_lines = abstract.split('\n')
    first_3_lines = '\n'.join(abstract_lines[:3])

    css_styles = """
    <style>
    .article-card {
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #ddd;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transition: transform 0.2s ease-in-out;
    }
    .article-card:hover {
        transform: translateY(-5px);
    }
    .article-title {
        font-size: 1.5em;
        color: #333;
        font-weight: bold;
        text-decoration: none;
        margin-bottom: 10px;
        display: block;
    }
    .article-title:hover {
        text-decoration: underline;
    }
    .article-authors, .article-details {
        color: #777;
    }
    .article-details p {
        margin: 5px 0;
    }
    </style>
    """

    st.markdown(css_styles, unsafe_allow_html=True)

    st.markdown(f"""
    <div class='article-card'>
        <a href="{article['url']}" class='article-title'>{article['title']}</a>
        <div class='article-authors'>Authors: {', '.join(article['authors'])}</div>
        <div class='article-details'>
            <p>Published: {article['published']}</p>
            <p>Source: {article['source']}</p>
            <p>{first_3_lines}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    logger.info(f"Displayed article: {article['title']}")

# Main logic for generating response
if generate or st.session_state.enter_pressed:
    if user_input == "":
        st.warning("Please enter a message ⚠️")
    else:
        # Reset the enter_pressed state
        st.session_state.enter_pressed = False
        
        with st_lottie_spinner(loading_animation):
            logger.info(f"User input: {user_input}")

            # Extract keywords
            keywords = extract_keywords(st.session_state.thread.id, user_input)
            logger.info(f"Keywords: {keywords}")

            # Define number of results based on length selection
            num_results = 10 if length_selection == "Parent" else 15

            # Initialize an empty list to store all articles
            all_articles = []

            # Search NCBI
            ncbi_articles = search_ncbi(keywords, num_results)
            all_articles.extend(ncbi_articles)

            if not all_articles:
                st.warning("No specific articles found. The response will be based on general knowledge.")

            # Create context for response generation
            context = "\n\n".join(
                f"Title: {article['title']}\nAuthors: {', '.join(article['authors'])}\nPublished: {article['published']}\nAbstract: {article['abstract']}"
                for article in all_articles
                if article['title'] and article['abstract'] and article['authors']
            ) or "No specific articles found. Please provide a general response based on your knowledge."

            # Generate response
            full_response, text_message = generate_response(st.session_state.user_input, length_selection, context, response_placeholder)

            # Display the full response
            st.subheader("")
            response_placeholder.markdown(full_response)
            
            # Display the text message version
            st.subheader("Text Message Version")
            st.markdown(text_message)

            # Display the articles
            st.subheader("Considered Articles")
            for article in all_articles:
                display_article_card(article, is_dark_mode=False)
                logger.info(f"Article displayed: {article['title']}")
