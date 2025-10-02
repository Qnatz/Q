# Example 1: Simple web app
template = llm_service.generate_dynamic_template(
    language="python",
    project_type="web",
    requirements="A blog application with user authentication and post management",
    framework="django",
    database="postgresql",
    auth_method="jwt",
    deployment="docker"
)

# Example 2: From natural language
template = llm_service.generate_template_from_prompt(
    "Create a React frontend with Node.js backend for an e-commerce site with MongoDB and JWT authentication"
)

# Example 3: Mobile app
template = llm_service.generate_dynamic_template(
    language="kotlin",
    project_type="mobile", 
    requirements="Weather app with location services and offline support",
    framework="android",
    deployment="playstore"
)

# Analyze template quality
analysis = llm_service.analyze_template_quality(template, "python")
print(f"Template quality score: {analysis['score']}/100")

# Save template to files
for file_path, content in template.items():
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(content)
