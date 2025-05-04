# Confluence Source Editor

A Python tool to create or update Confluence pages from markdown files using templates and AI-powered content merging.

## Overview

This tool allows you to:
- Convert markdown files to Confluence pages
- Use Confluence templates with intelligent content mapping
- Automatically generate appropriate page titles
- Create pages with proper parent-child relationships
- Process code blocks and formatting correctly

The tool leverages Google's Gemini AI to intelligently map content from your markdown files to Confluence templates, helping maintain consistent documentation structure while allowing the flexibility of markdown authoring.

## Prerequisites

- Python 3.7+
- Confluence instance with API access
- Google Gemini API key

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/confluence-source-editor.git
   cd confluence-source-editor
   ```

2. Install required dependencies:
   ```bash
   pip install atlassian-python-api google-genai markdown argparse
   ```

3. Set up environment variables:
   ```bash
   export CONFLUENCE_URL="https://your-instance.atlassian.net"
   export CONFLUENCE_USERNAME="your_email@example.com"
   export CONFLUENCE_API_TOKEN="your-api-token"
   export GEMINI_API_KEY="your-gemini-api-key"
   ```

## Usage

Basic usage:
```bash
python main.py --markdown-file="./your-document.md"
```
## Attachment Support

The tool supports attaching files to your Confluence pages with automatic link creation:

```bash
python main.py --markdown-file="./docs.md" --attach="./diagram1.png" --attach="./data.csv"
```

## Command Line Arguments
The tool accepts the following command line arguments:


| Argument | Description | Default |
|----------|-------------|---------|
| `--markdown-file` | Path to markdown file (required) | - |
| `--template-name` | Name of Confluence template to use | - |
| `--no-template` | Skip template processing | False |
| `--space` | Confluence space key | "DBT" |
| `--title` | Page title | Auto-generated |
| `--parent-page` | Name of parent page | - |
| `--attach` | Path to file(s) to attach to the page (can be used multiple times) | - |

### Examples

**Create a page using a template:**
```bash
python main.py --template-name="DevOps Runbook" --markdown-file="./runbook.md" --space="OPS" --title="New Service Deployment"
```

**Create a page without a template:**
```bash
python main.py --no-template --markdown-file="./release-notes.md" --space="REL"
```

**Create a page as a child of another page:**
```bash
python main.py --markdown-file="./service-docs.md" --parent-page="Backend Services"
```

**Create a page with auto-generated title:**
```bash
python main.py --template-name="Technical Design" --markdown-file="./design.md"
```

**Create a page with attachments:**
```bash
python main.py --markdown-file="./report.md" --attach="./image.png" --attach="./data.csv"
```

## Features

### Template Integration
When a template is specified, the tool:
1. Fetches the template from your Confluence instance
2. Uses AI to map markdown content to appropriate sections in the template
3. Preserves template structure while adding your content

### Direct Markdown Processing
When `--no-template` is used or no template is found:
1. Converts markdown directly to Confluence-compatible HTML
2. Preserves all formatting including code blocks, tables, and lists

### Intelligent Title Generation
When no title is specified:
1. Creates titles in the format "New Generated Document XXX"
2. Automatically increments numbers (001, 002, etc.)
3. Ensures unique titles within the space

### Parent Page Support
When `--parent-page` is specified:
1. Locates the named page within the chosen space
2. Creates the new page as a child of that page
3. Maintains your documentation hierarchy

### Attachment Support
When `--attach` is used:
1. Uploads specified files to the created Confluence page
2. Ensures files are accessible and linked within the page
3. Supports multiple attachments by allowing the `--attach` argument to be used multiple times
4. Automatically handles file uploads during page creation or update

## Troubleshooting

**Template not found**
- Check that the template name matches exactly (case-sensitive)
- Verify your API token has access to templates

**Content truncation**
- For very large documents, the tool includes a safety check
- If truncation is detected, it will append the full content

**API errors**
- Ensure all environment variables are set correctly
- Check your Confluence API token permissions
- Verify your Gemini API key is valid

**Markdown formatting issues**
- Ensure your markdown is valid and follows standard conventions
- Check for any unsupported markdown features that may cause issues
- Use the `--no-template` option to bypass template processing if needed
- Ensure your markdown files are properly encoded in UTF-8

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## Acknowledgments

- [Atlassian Python API](https://atlassian-python-api.readthedocs.io/)
- [Google Genai Python Library](https://googleapis.github.io/python-genai/)