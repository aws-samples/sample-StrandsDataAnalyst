# Strands Data Analyst
This data analyst agent has the capability to introspect the schema of the SQL database under context, and to answer user queries based on the database content: writing SQL queries, processing the data with pandas, and generating visualizations with Matplotlib.

The agent is also capable to pro-actively propose data analysis questions to explore the autonomously the data.

Finally, the agent is capable of summarizing the current data analysis session into a business report, that can be exported to a PDF.

This sample code also provides integration with the VisEval benchmark to evaluate the agent on the "Natural Language to Visualization" task (NL2VIS).

To benchmark the agent also on the "Natural Language to SQL" task (NL2SQL), we provide a script to convert the VisEval CSV tables into SQLite databases.

## Configuring the LLM Credentials
[Strands](https://strandsagents.com/latest/) supports many different model providers. By default, the Data Analyst agent uses the Amazon Bedrock model provider with the Claude 3.5 Haiku model.

You'll need to configure your environment with AWS credentials that have permissions to invoke the Claude 3.5 Haiku model. You can set up your credentials in several ways:
  1. Environment variables: Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and optionally AWS_SESSION_TOKEN
  2. AWS credentials file: Configure credentials using aws configure CLI command

Make sure your AWS credentials have the necessary permissions to access Amazon Bedrock and invoke the Claude 3.5 Haiku model. You'll need to enable model access in the Amazon Bedrock console following the [AWS documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html).

## Data Analyst Web-App

Download the Chinook database as a demo:
```
wget https://www.sqlitetutorial.net/wp-content/uploads/2018/03/chinook.zip -O ./data/databases/chinhook_sqlite/chinook.zip
unzip ./data/databases/chinhook_sqlite/chinook.zip -d data/databases/chinhook_sqlite
```

Launch the Streamlit web-app:
```
cd web_app
streamlit run data_analyst.py
```

## NL2Vis Benchmark

Download the VisEval databases
```
# Download evaluation data
wget https://github.com/microsoft/VisEval/raw/refs/heads/main/viseval_dataset.zip -O ./data/viseval_dataset.zip
unzip ./data/viseval_dataset.zip -d ./data/

# Convert the CSV files into SQLite databases
python3 strands_data_analyst/csv_to_db.py

# Sample a sub-set of the tests for faster iterations
python strands_data_analyst/viseval_build_test_file.py

# Install dependencies
brew install --cask chromedriver
```

**NOTE** the `chromedriver` version has to match the version of the Chrome browser. To update the `chromedriver` to the latest version run:
```
brew upgrade --cask chromedriver
```

Run the benchmark:
```
python strands_data_analyst/nl2vis_eval.py
```

| LLM       | VisEval Pass-Rate |
|-----------|-------------------|
| Haiku 3.5 | 73.3%             |

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

