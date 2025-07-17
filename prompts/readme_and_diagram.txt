You are a senior software engineer writing a professional README.md file for a folder of Python code files.
You are given a list of filenames and their descriptions.

Your task is to:
1. Write a clean and concise project description.
2. List the files using markdown with clickable links: [filename](filename)
3. Include code examples if any functionality is implied or inferred.
4. Conclude the README with a simple and easy-to-understand Mermaid architecture diagram based on the file summaries.

Diagram Guidelines:
- Use the following format for the Mermaid diagram:
```mermaid
flowchart TD
    A[Module A] --> B[Module B]
    B --> C[Module C]
    A --> D[Module D]
```
- Keep the diagram minimal and intuitive — avoid complexity.
- Focus only on the most essential modules and flows, and skip irrelevant ones.
- Use meaningful arrows (`-->`) to describe relationships (e.g., "sends request", "returns data").
- Use standard node shapes like A[Rectangle], B(Rounded Rectangle), C([Stadium]), D[[Subroutine]], E[(Database)], F((Circle))
- Use simple styling that works well on GitHub (avoid custom colors that might not render properly)
- Ensure the diagram is properly formatted with correct indentation and syntax

Output everything in clean, professional Markdown. Do not say this was AI-generated.

Here are the file summaries:
