"""
This script generates or updates Markdown files for tools based on a JSON index.
It reads the tool data from `index.json`, validates the required fields, and formats the features
section. If the Markdown file already exists, it updates the features section; otherwise, it creates
a new Markdown file with the full content.
"""

import json
import os
import re
import shutil

FEATURES_START = "<!-- FEATURES:START -->"
FEATURES_END = "<!-- FEATURES:END -->"


def format_features(features):
    """
    Formats a list of features into a Markdown block with start and end markers.

    Args:
        features (list): List of feature strings.

    Returns:
        str: Formatted Markdown string for the features section.
    """
    return (
        FEATURES_START
        + "\n"
        + "\n".join(f"- {f}" for f in features)
        + "\n"
        + FEATURES_END
    )


def update_features_section(content, new_features_block):
    """
    Updates or inserts the features section in the given Markdown content.

    Args:
        content (str): The original Markdown content.
        new_features_block (str): The formatted features block to insert or update.

    Returns:
        str: The updated Markdown content with the new features section.
    """
    # Replace or insert the FEATURES block
    pattern = re.compile(f"{FEATURES_START}.*?{FEATURES_END}", re.DOTALL)
    if FEATURES_START in content and FEATURES_END in content:
        return pattern.sub(new_features_block, content)

    # Insert after "## 🚀 Key Features"
    if "## 🚀 Key Features" in content:
        return content.replace(
            "## 🚀 Key Features", "## 🚀 Key Features\n\n" + new_features_block
        )

    # Append at the end as fallback
    return content + "\n\n## 🚀 Key Features\n\n" + new_features_block


def validate_tool(tool, required_fields):
    """
    Validates that all required fields are present in the tool dictionary.

    Args:
        tool (dict): The tool data to validate.
        required_fields (list): List of required field names.

    Raises:
        ValueError: If any required field is missing from the tool.
    """
    for field in required_fields:
        if field not in tool:
            raise ValueError(
                f"Missing required field '{field}' in tool: {tool.get('name', '[unknown]')}"
            )

def generate_full_content(tool, features_block):
    """
    Generates the full Markdown content for a tool based on its data.

    Args:
        tool (dict): The tool data containing all necessary fields.
        features_block (str): The formatted features block to include.

    Returns:
        str: The complete Markdown content for the tool.
    """
    return f"""# {tool["name"]}

<img src="{tool['logo_url']}" alt="{tool['name']} Logo" style="height: 96px;" />

**Version:** {tool["version"]}  \

**Release Date:** {tool["release_date"]}  \

**License:** [{tool["license"]}]({tool["license_url"]})  \

**Platforms:** {", ".join(tool["platforms"])}  \


---

## 🧩 Description

{tool["description"]}

---

## 🚀 Key Features

{features_block}

---

## 🌐 Official Links

- 🔗 Website: [{tool["website"]}]({tool["website"]})
- 📥 Download: [{tool["download_url"]}]({tool["download_url"]})
- 📚 Documentation: [{tool["documentation_url"]}]({tool["documentation_url"]})
- 💻 Source Code: [{tool["repository_url"]}]({tool["repository_url"]})

---

## 🖼️ Screenshot

![Screenshot]({tool["screenshot_url"]})

---

## 🏷️ Tags

{", ".join(tool["tags"])}

---

## 🔧 Tech Stack

- **Languages:** {", ".join(tool["language"])}
- **License:** {tool["license"]}
- **Status:** {tool["status"]}
"""

def format_tool_list(tools):
    """
    Generates a Markdown table from the tools list for the README.
    Args:
        tools (list): List of tool dictionaries.

    Returns:
        str: Markdown formatted table of tools.
    """
    header = "| Tool | Category | Platforms | License | Details |\n"
    divider = "|------|----------|-----------|---------|---------|\n"
    rows = []
    for tool in tools:
        name = tool["name"]
        category = tool["category"]
        platforms = ", ".join(tool["platforms"])
        license_ = tool["license"]
        link = f"[Website]({tool['website']})"
        md_link = f"[{name}](docs/tools/{tool['slug']}.md)"
        rows.append(f"| {md_link} | {category} | {platforms} | {license_} | {link} |")

    return (
        "<!-- TOOLLIST:START -->\n"
        + header
        + divider
        + "\n".join(rows)
        + "\n<!-- TOOLLIST:END -->"
    )

def update_tool_list_in_readme(tools, readme_path="README.md"):
    """
    Updates the Tool List section in README.md if it exists and differs.
    Args:
        tools (list): List of tool dictionaries.
        readme_path (str): Path to the README.md file.
    Raises:
        FileNotFoundError: If the README.md file does not exist.
    Raises:
        ValueError: If the tools list is empty or not provided.
    """
    if not os.path.exists(readme_path):
        print("README.md not found — skipping Tool List update.")
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_table = format_tool_list(tools)
    pattern = re.compile(r"<!-- TOOLLIST:START -->.*?<!-- TOOLLIST:END -->", re.DOTALL)

    if pattern.search(content):
        updated_content = pattern.sub(new_table, content)
        if content.strip() != updated_content.strip():
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            print("Updated Tool List in README.md")
        else:
            print("Tool List in README.md is up to date.")
    else:
        print("TOOLLIST markers not found in README.md — skipping update.")

def update_index():
    """
    Reads the index.json file, removes duplicates by slug, sorts by name,
    and writes the updated list back to index.json.
    """
    # Read the index.json file
    with open("index.json", "r", encoding="utf-8") as f:
        tools = json.load(f)

    # Remove duplicates by slug
    seen = set()
    tools = [t for t in tools if not (t["slug"] in seen or seen.add(t["slug"]))]

    # Sort alphabetically by name
    tools.sort(key=lambda t: t["name"].lower())

    # Write the updated list back to index.json
    with open("index.json", "w", encoding="utf-8") as f:
        json.dump(tools, f, indent=2, ensure_ascii=False)

    print("Sorted and updated index.json")
    return tools

def main():
    """
    Main function to read the JSON index, validate tools, and generate or update Markdown files.
    """
    # Define the required fields for each tool
    required_fields = [
        "name",
        "slug",
        "description",
        "version",
        "release_date",
        "platforms",
        "license",
        "license_url",
        "category",
        "website",
        "download_url",
        "repository_url",
        "documentation_url",
        "screenshot_url",
        "logo_url",
        "tags",
        "language",
        "status",
        "features",
    ]

    tools = update_index()

    os.makedirs("docs/tools", exist_ok=True)

    for tool in tools:
        validate_tool(tool, required_fields)

        features_block = format_features(tool["features"])
        markdown_path = f"docs/tools/{tool['slug']}.md"

        # Generate full content
        full_generated_content = generate_full_content(tool, features_block)

        if os.path.exists(markdown_path):
            with open(markdown_path, "r", encoding="utf-8") as f:
                current_content = f.read()

            # Compare entire content
            if current_content.strip() != full_generated_content.strip():
                with open(markdown_path, "w", encoding="utf-8") as f:
                    f.write(full_generated_content)
                print(f"Updated {markdown_path}")
            else:
                print(f"No changes in {markdown_path} — skipped.")
        else:
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(full_generated_content)
            print(f"Created {markdown_path}")

    update_tool_list_in_readme(tools)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shutil.copyfile(
        os.path.join(root_dir, "index.json"),
        os.path.join(root_dir, "docs", "index.json")
    )
    print("Copied index.json to docs/index.json")

if __name__ == "__main__":
    main()
