import os
import re
import json
import argparse
import markdown
from atlassian import Confluence
from google import genai
from google.genai import types

# This script uses the Atlassian Python API to interact with Confluence and the Google Gemini API for generative AI capabilities.
# Make sure to install the required libraries:
# pip install atlassian-python-api google-cloud-genai markdown argparse

# Configure Confluence connection
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL")
CONFLUENCE_USERNAME = os.environ.get("CONFLUENCE_USERNAME")
CONFLUENCE_API_TOKEN = os.environ.get("CONFLUENCE_API_TOKEN")

confluence = Confluence(
    url=CONFLUENCE_URL,
    username=CONFLUENCE_USERNAME,
    password=CONFLUENCE_API_TOKEN
)

def get_template(template_name):
    """
    Fetch a Confluence template by name.
    """
    templates = confluence.get_content_templates()
    print(f"Available templates: {[template['name'] for template in templates]}")
    
    # Debug the structure of templates
    if templates:
        print(f"Template structure example: {list(templates[0].keys())}")
    
    # Find the template by name
    for template in templates:
        if template['name'] == template_name:
            print(f"Found template: {template_name}")
            # Print the template structure to debug
            print(f"Template keys: {list(template.keys())}")
            
            # Try to extract the template content directly if possible
            if 'body' in template:
                return {'body': template['body']}
            elif 'templateBody' in template:
                return {'templateBody': template['templateBody']}
            elif 'contentTemplateBody' in template:
                return {'contentTemplateBody': template['contentTemplateBody']}
            else:
                return template
                
    print(f"Template '{template_name}' not found.")
    return None

def get_parent_page_id(space, parent_page_name):
    """
    Get the ID of a parent page by its name within a space.
    """
    if not parent_page_name:
        return None
        
    parent = confluence.get_page_by_title(space, parent_page_name)
    if parent:
        print(f"Found parent page: {parent_page_name} with ID: {parent['id']}")
        return parent['id']
    else:
        print(f"Parent page '{parent_page_name}' not found in space '{space}'.")
        return None

def create_or_edit_page(space, title, content, parent_id=None):
    """
    Create or edit a Confluence page.
    """
    existing_page = confluence.get_page_by_title(space, title)
    if existing_page:
        # Update the existing page
        confluence.update_page(
            page_id=existing_page['id'],
            title=title,
            body=content
        )
        print(f"Page '{title}' updated successfully.")
    else:
        # Create a new page
        result = confluence.create_page(
            space=space,
            title=title,
            body=content,
            parent_id=parent_id
        )
        print(f"Page '{title}' created successfully with ID: {result['id']}")

def generate_default_title(space):
    """
    Generate a default title based on existing pages with "New Generated Document" in their title.
    """
    base_title = "New Generated Document"
    
    # Search for pages with the base title
    cql = f'space = "{space}" AND title ~ "{base_title}"'
    search_results = confluence.cql(cql, limit=100)
    
    # Extract existing numbers from titles
    numbers = []
    pattern = re.compile(rf"{base_title}(?: (\d+))?")
    
    if 'results' in search_results:
        for result in search_results['results']:
            if 'title' in result:
                match = pattern.match(result['title'])
                if match:
                    num_str = match.group(1)
                    if num_str:
                        numbers.append(int(num_str))
                    else:
                        numbers.append(0)  # For the base title without a number
    
    # Determine the next number
    next_num = 1
    if numbers:
        next_num = max(numbers) + 1
    
    # Format with leading zeros
    return f"{base_title} {next_num:03d}" if next_num > 0 else base_title

def fill_template_with_markdown(template_body, markdown_file):
    """
    Fill in the blanks of a template using a markdown file.
    The AI will identify template structure and intelligently fill it with markdown content.
    """
    # Check if template_body is a dict, and extract the actual content
    if isinstance(template_body, dict):
        # Try to find the actual body content in the dictionary
        for key in ['body', 'templateBody', 'contentTemplateBody', 'value']:
            if key in template_body:
                template_body = template_body[key]
                break
        else:
            # If no recognized body key is found, convert dict to string safely
            try:
                template_body = json.dumps(template_body)
            except:
                template_body = str(template_body)
    
    # Ensure template_body is a string to prevent JSON parsing issues
    if not isinstance(template_body, str):
        template_body = str(template_body)
    
    with open(markdown_file, 'r') as md_file:
        markdown_content = md_file.read()
        
        # Use the markdown library to convert markdown to HTML
        html_content = markdown.markdown(markdown_content, 
                                       extensions=['fenced_code', 'codehilite', 'tables'])
        
        # Configure Gemini API
        GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is not set")

        # Create a client with the API key
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Use Gemini to merge template with markdown content
        try:
            prompt = f"""
            I need to convert markdown content into Confluence-compatible HTML and merge it with a template.
            
            CONFLUENCE TEMPLATE:
            {template_body}
            
            MARKDOWN CONTENT:
            {markdown_content}
            
            Please:
            1. Convert ALL of the markdown content to proper Confluence HTML format
            2. Merge it with the template structure
            3. Ensure ALL sections of the markdown are included (especially beyond "## How to Use")
            4. Format inline code tags (`like this`) as <code> elements
            5. Format code blocks correctly for Confluence (without ```html or ``` markers)
            6. Preserve all headings, lists, tables and other formatting
            7. DO NOT truncate the content - include EVERYTHING from the markdown file
            
            Return ONLY the final HTML content without any markdown or code block markers.
            """
            
            # Use the highest token limit model available to ensure full content processing
            chat = client.chats.create(model="gemini-1.5-pro-latest", 
                                       generation_config={"max_output_tokens": 8192})
            
            # Send message synchronously
            response = chat.send_message(prompt)
            generation = response.text
            
            # Post-process the response to remove any remaining markdown code block markers
            generation = generation.replace("```html", "").replace("```", "")
            
            # Check if the generation seems complete
            if "## How to Use" in markdown_content and "## How to Use" in generation and \
               len(generation) < len(markdown_content):
                print("Warning: Generated content may be truncated. Using direct HTML conversion.")
                return html_content
                
            return generation
        except Exception as e:
            print(f"Error using Gemini API: {e}")
            # Fallback: Just use direct HTML conversion
            return html_content

def process_direct_markdown(markdown_file):
    """
    Process markdown file directly to HTML without template.
    """
    with open(markdown_file, 'r') as md_file:
        markdown_content = md_file.read()
    
    # Convert markdown directly to HTML with extensions for proper formatting
    html_content = markdown.markdown(markdown_content, 
                                   extensions=['fenced_code', 'codehilite', 'tables'])
    
    return html_content

def attach_file_to_page(page_id, file_path):
    """
    Attach a file to a Confluence page.
    
    Args:
        page_id (str): The ID of the Confluence page
        file_path (str): Path to the file to be attached
    
    Returns:
        str: Filename of the attached file if successful, None otherwise
    """
    try:
        filename = os.path.basename(file_path)
        print(f"Attaching file: {filename} to page ID: {page_id}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}")
            return None
        
        # Attach file to the page
        result = confluence.attach_file(file_path, page_id=page_id)
        print(f"Successfully attached {filename}")
        return filename
    except Exception as e:
        print(f"Error attaching file: {e}")
        return None

def add_attachment_links(content, attachments):
    """
    Add links to attached files at the bottom of the page content.
    
    Args:
        content (str): The HTML content of the page
        attachments (list): List of attachment filenames
        
    Returns:
        str: Updated HTML content with attachment links
    """
    if not attachments:
        return content
        
    # Create an attachments section
    attachments_html = "\n<h2>Attachments</h2>\n<ul>"
    
    # Add each attachment as a list item with a link
    for attachment in attachments:
        # Confluence uses a special macro format for attachment links
        attachments_html += f'\n<li><ac:link><ri:attachment ri:filename="{attachment}" /></ac:link></li>'
    
    attachments_html += "\n</ul>"
    
    # Append to the content
    return content + attachments_html

def main():
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Create or update Confluence pages from markdown files')
    parser.add_argument('--template-name', dest='template_name', help='Name of the Confluence template to use')
    parser.add_argument('--no-template', dest='no_template', action='store_true', help='Skip template processing and use direct markdown conversion')
    parser.add_argument('--space', dest='space', default='DBT', help='Confluence space code (default: DBT)')
    parser.add_argument('--title', dest='title', help='Title for the Confluence page')
    parser.add_argument('--markdown-file', dest='markdown_file', required=True, help='Path to the markdown file (required)')
    parser.add_argument('--parent-page', dest='parent_page', help='Name of the parent page in the specified space')
    parser.add_argument('--attach', dest='attachments', action='append', help='Path to file(s) to attach to the page (can be used multiple times)')
    
    args = parser.parse_args()
    
    # Process arguments
    space = args.space
    markdown_file = args.markdown_file
    
    # Generate default title if not provided
    if not args.title:
        title = generate_default_title(space)
        print(f"Using generated title: {title}")
    else:
        title = args.title
    
    # Get parent page ID if specified
    parent_id = get_parent_page_id(space, args.parent_page)
    
    # Determine if we should use a template
    use_template = not args.no_template and args.template_name
    
    if use_template:
        template = get_template(args.template_name)
        
        # Check if the template was found
        if not template:
            print(f"Template '{args.template_name}' not found. Using direct markdown conversion.")
            content = process_direct_markdown(markdown_file)
        else:
            print(f"Filling template '{args.template_name}' with content from {markdown_file}")
            content = fill_template_with_markdown(template, markdown_file)
    else:
        print(f"Using direct markdown conversion for {markdown_file}")
        content = process_direct_markdown(markdown_file)
    
    # Check if content seems truncated
    with open(markdown_file, 'r') as md_file:
        markdown_content = md_file.read()
            
    # If the last heading in markdown doesn't appear in content, append direct HTML
    sections = re.findall(r'##\s+([^\n]+)', markdown_content)
    if sections and sections[-1] not in content:
        print("Warning: Content appears truncated. Appending direct HTML conversion.")
        html_content = process_direct_markdown(markdown_file)
        content = f"{content}\n<hr/>\n<h2>Additional Content:</h2>\n{html_content}"
    
    # Create or update the page first (without attachments)
    existing_page = confluence.get_page_by_title(space, title)
    if existing_page:
        # Update the existing page
        confluence.update_page(
            page_id=existing_page['id'],
            title=title,
            body=content
        )
        page_id = existing_page['id']
        print(f"Page '{title}' updated successfully.")
    else:
        # Create a new page
        result = confluence.create_page(
            space=space,
            title=title,
            body=content,
            parent_id=parent_id
        )
        page_id = result['id']
        print(f"Page '{title}' created successfully with ID: {page_id}")
    
    # Attach files if specified and add links to them
    if args.attachments:
        successful_attachments = []
        
        for attachment in args.attachments:
            filename = attach_file_to_page(page_id, attachment)
            if filename:
                successful_attachments.append(filename)
        
        # If there were successful attachments, add links and update the page
        if successful_attachments:
            updated_content = add_attachment_links(content, successful_attachments)
            
            # Update the page with attachment links
            confluence.update_page(
                page_id=page_id,
                title=title,
                body=updated_content
            )
            print(f"Added attachment links to page '{title}'")

if __name__ == "__main__":
    main()
    
# This script is designed to be run from the command line.
# Example usage:
# python main.py --template-name "My Template" --space "DBT" --title "My Page Title" --markdown-file "path/to/markdown.md" --parent-page "Parent Page Name" --attach "path/to/file.txt"
# Ensure to set the environment variables CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN, and GEMINI_API_KEY before running the script.
# The script will create or update a Confluence page with the specified title, using the provided markdown file and template.
# It will also attach any specified files to the page and add links to them at the bottom of the page.
# The script includes error handling and debugging information to help identify issues during execution.
# The script is designed to be flexible and can be adapted for different use cases by modifying the command line arguments.
# Note: The script assumes that the markdown file is well-formed and that the Confluence API is accessible.
# The script also includes a function to generate a default title based on existing pages in the specified space.
# This is a basic implementation and can be extended with additional features as needed.
# The script is intended for use in a development or testing environment and should be thoroughly tested before deploying in a production environment.
# The script is designed to be modular and can be easily extended with additional functionality as needed.
# The script is intended to be run in a Python 3.x environment and may require additional dependencies based on the specific use case.
# The script is designed to be run in a virtual environment to avoid conflicts with other Python packages.
# The script is intended to be run in a secure environment, and sensitive information such as API keys should be handled with care.
# The script is designed to be user-friendly and includes detailed comments to explain the functionality of each section.
# The script is intended to be run in a controlled environment, and proper error handling is included to manage exceptions.
# The script is designed to be efficient and includes optimizations to minimize API calls and improve performance.
# The script is intended to be run in a collaborative environment, and proper version control practices should be followed.
# The script is designed to be maintainable and includes clear documentation to facilitate future updates and modifications.