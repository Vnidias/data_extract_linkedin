# LinkedIn Jobs Scraper & Browser 🔎💼

An interactive web application for scraping, enhancing, and browsing LinkedIn job postings using the ScrapingDog API. This tool is designed for powerful, controlled data collection and features an integrated Streamlit UI for a seamless user experience.

-----

## ✨ Features

  * **Interactive UI**: A polished Streamlit interface to control scraping parameters, view results, and analyze data.
  * **AI-Powered Enhancement**: Automatically extracts structured data (skills, tools, languages) from job descriptions using OpenAI.
  * **Advanced Scraping Control**: Fine-tune your data collection with precise limits (`MAX_OVERVIEWS`, `MAX_LISTINGS`), delays, and job filters.
  * **Dynamic Keyword Management**: Interactively add and remove multiple job titles for targeted, multi-faceted searches.
  * **Data Normalization**: On-the-fly cleaning of data, including standardizing job types (`remote`, `hybrid`, `on-site`), locations, and technical skills.
  * **Rich Visualizations**: In-app dashboards and graphs to analyze trends in job postings, top companies, required skills, and more.
  * **Graceful Operation**: Built-in support to cancel an ongoing scrape and process all data collected up to that point without loss.
  * **Persistent Sessions**: Automatically loads the results from your most recent scrape when you restart the app.

-----

## 🗂️ Project Structure

The project is organized into a modular structure for clarity and maintainability.

```
.
├── streamlit_app.py                # Main application file (runs the UI)
├── li_july_2025_with_desc.py       # Core scraping and file export logic
├── ui/                             # Python modules for the Streamlit UI
│   ├── components.py               # UI element generators (e.g., job cards)
│   ├── config.py                   # Central configuration and settings
│   ├── data_processing.py          # Data cleaning and normalization pipeline
│   ├── extraction.py               # OpenAI integration for data enrichment
│   ├── graphs.py                   # Code for the "Graphs & DQ" tab
│   ├── visualization.py            # Code for the "Insights" tab charts
│   └── workflow.py                 # Renders the project workflow diagram
├── css/
│   └── app.css                     # Custom styling for the web app
├── templates/
│   └── card.html                   # HTML template for job cards
├── exports/                        # Default directory for saved CSV/JSON files
├── requirements.txt                # Project dependencies
└── README.md                       # This file
```

-----

## 🚀 Quick Start

### 1\. Prerequisites

  * Python 3.10+
  * A **ScrapingDog API key**.
  * An optional **OpenAI API key** for data enhancement.

### 2\. Installation

Clone the repository and install the required Python libraries.

```bash
# Clone this repository
git clone <your-repo-url>
cd <your-repo-folder>

# Install dependencies
pip install -r requirements.txt
```

### 3\. Running the Application

Launch the Streamlit application from your terminal.

```bash
streamlit run streamlit_app.py
```

Your web browser will open a new tab with the application running.

-----

## ⚙️ How to Use the App

1.  **Enter API Keys**: Paste your ScrapingDog and (optional) OpenAI API keys into the sidebar.
2.  **Set Keywords**: Use the interactive keyword input to add one or more job titles (e.g., "data engineer," "data analyst").
3.  **Configure Parameters**:
      * **Search**: Choose a country, location, and sorting options.
      * **Credits & Timing**: Set `MAX_OVERVIEWS` and `MAX_LISTINGS` to the same number (e.g., 100) for a predictable number of results.
      * **File Output**: Give your export file a name.
4.  **Run Scrape**: Click the **"Run scrape 🚀"** button.
5.  **Monitor & Cancel (Optional)**: Watch the progress in the status box. Once the "Overviews" count reaches your target, you can click **"Cancel scrape"** to stop collecting and immediately process the results.
6.  **Explore**: Use the tabs ("Explore," "Insights," "Graphs") to search, filter, and analyze the collected data.

-----

## 🧠 How It Works

1.  **UI Layer (`streamlit_app.py`)**: Captures your parameters and keywords.
2.  **Scraping Layer (`li_july_2025_with_desc.py`)**: Makes API calls to ScrapingDog to fetch raw job listings and descriptions.
3.  **Enrichment Layer (`ui/extraction.py`)**: Sends job descriptions to OpenAI to extract structured information like skills and tools.
4.  **Processing Layer (`ui/data_processing.py`)**: Cleans and normalizes the combined raw and AI-enhanced data.
5.  **Visualization Layer (`ui/graphs.py`, `ui/visualization.py`)**: Renders the final, clean DataFrame as interactive charts and tables.
6.  **File Output**: The fully processed data is saved to the `exports/` directory, ready to be automatically loaded the next time you start the app.
