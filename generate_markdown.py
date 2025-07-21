"""
This script generates or updates Markdown files for tools based on a JSON index.
It reads the tool data from `index.json`, validates the required fields, and formats the features
section. If the Markdown file already exists, it updates the features section; otherwise, it creates
a new Markdown file with the full content.
"""

import json
import os
import re

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
        "markdown_file",
        "status",
        "features",
    ]

    with open("index.json", "r", encoding="utf-8") as f:
        tools = json.load(f)

    os.makedirs("tools", exist_ok=True)

    for tool in tools:
        validate_tool(tool, required_fields)

        features_block = format_features(tool["features"])
        markdown_path = tool["markdown_file"]

        if os.path.exists(markdown_path):
            with open(markdown_path, "r", encoding="utf-8") as f:
                current_content = f.read()

            # Generate full content for comparison
            full_generated_content = f"""# {tool["name"]}

![{tool["name"]} Logo]({tool["logo_url"]})

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

            # Compare entire content
            if current_content.strip() != full_generated_content.strip():
                with open(markdown_path, "w", encoding="utf-8") as f:
                    f.write(full_generated_content)
                print(f"Updated {markdown_path}")
            else:
                print(f"No changes in {markdown_path} — skipped.")


if __name__ == "__main__":
    main()
