// docs/js/markdown.js
export async function renderMarkdownFile(containerId, markdownPath) {
  const container = document.getElementById(containerId);

  try {
    const response = await fetch(markdownPath);
    if (!response.ok) {
      throw new Error(`Failed to fetch ${markdownPath}`);
    }

    const markdown = await response.text();
    const html = marked.parse(markdown);
    container.innerHTML = html;
  } catch (error) {
    container.innerHTML = `
      <div class="notification is-danger">
        ⚠️ Could not load the file: ${markdownPath}
      </div>`;
    console.error(error);
  }
}