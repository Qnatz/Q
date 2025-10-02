class LLMService:
    def __init__(self, llm: UnifiedLLM, prompt_manager: PromptManager):
        self.llm = llm
        self.prompt_manager = prompt_manager
        self.language_configs = self._get_language_configs()
        self.best_practices = self._get_best_practices()
        self.template_service = DynamicTemplateService(self)  # Add template service
    
    # ... [keep all your existing methods] ...
    
    def generate_dynamic_template(
        self,
        language: str,
        project_type: str,
        requirements: str,
        framework: str = None,
        database: str = None,
        auth_method: str = None,
        deployment: str = None
    ) -> Dict[str, str]:
        """
        Generate a complete project template dynamically using AI
        
        Args:
            language: Programming language (python, javascript, etc.)
            project_type: Type of project (web, mobile, cli, microservice, etc.)
            requirements: Detailed project requirements
            framework: Specific framework (django, react, spring, etc.)
            database: Database system (postgresql, mongodb, etc.)
            auth_method: Authentication method (jwt, oauth, etc.)
            deployment: Deployment target (docker, aws, heroku, etc.)
        
        Returns:
            Dictionary with file paths as keys and file contents as values
        """
        return self.template_service.generate_project_template(
            language=language,
            project_type=project_type,
            requirements=requirements,
            framework=framework,
            database=database,
            auth_method=auth_method,
            deployment=deployment
        )
    
    def generate_template_from_prompt(self, user_prompt: str) -> Dict[str, str]:
        """
        Generate template from natural language prompt with automatic detection
        """
        # Auto-detect language and project type from prompt
        language = self._detect_language(user_prompt)
        project_type = self._detect_project_type(user_prompt)
        
        # Extract technical specifications
        specs = self._extract_technical_specs(user_prompt)
        
        return self.generate_dynamic_template(
            language=language,
            project_type=project_type,
            requirements=user_prompt,
            **specs
        )
    
    def _detect_project_type(self, prompt: str) -> str:
        """Detect project type from prompt"""
        prompt_lower = prompt.lower()
        
        project_types = {
            'web': ['website', 'web app', 'web application', 'frontend', 'backend', 'fullstack'],
            'mobile': ['mobile', 'android', 'ios', 'react native', 'flutter', 'app'],
            'cli': ['cli', 'command line', 'terminal', 'script', 'tool'],
            'microservice': ['microservice', 'api', 'rest', 'graphql', 'service'],
            'desktop': ['desktop', 'gui', 'application', 'windows', 'mac', 'linux'],
            'library': ['library', 'package', 'module', 'sdk'],
            'data': ['data', 'analysis', 'processing', 'etl', 'pipeline', 'machine learning'],
            'game': ['game', 'unity', 'unreal', '3d', '2d'],
        }
        
        for project_type, indicators in project_types.items():
            if any(indicator in prompt_lower for indicator in indicators):
                return project_type
        
        return 'web'  # Default fallback
    
    def _extract_technical_specs(self, prompt: str) -> Dict[str, str]:
        """Extract technical specifications from prompt"""
        prompt_lower = prompt.lower()
        
        specs = {}
        
        # Detect framework
        frameworks = {
            'django': ['django'],
            'flask': ['flask'],
            'fastapi': ['fastapi'],
            'react': ['react'],
            'vue': ['vue'],
            'angular': ['angular'],
            'spring': ['spring'],
            'express': ['express'],
        }
        
        for framework, indicators in frameworks.items():
            if any(indicator in prompt_lower for indicator in indicators):
                specs['framework'] = framework
                break
        
        # Detect database
        databases = {
            'postgresql': ['postgres', 'postgresql'],
            'mongodb': ['mongo', 'mongodb'],
            'mysql': ['mysql'],
            'sqlite': ['sqlite'],
            'redis': ['redis'],
        }
        
        for database, indicators in databases.items():
            if any(indicator in prompt_lower for indicator in indicators):
                specs['database'] = database
                break
        
        # Detect authentication
        auth_methods = {
            'jwt': ['jwt', 'json web token'],
            'oauth': ['oauth'],
            'firebase': ['firebase auth', 'firebase authentication'],
        }
        
        for auth, indicators in auth_methods.items():
            if any(indicator in prompt_lower for indicator in indicators):
                specs['auth_method'] = auth
                break
        
        # Detect deployment
        deployments = {
            'docker': ['docker', 'container'],
            'aws': ['aws', 'amazon web services'],
            'heroku': ['heroku'],
            'netlify': ['netlify'],
        }
        
        for deployment, indicators in deployments.items():
            if any(indicator in prompt_lower for indicator in indicators):
                specs['deployment'] = deployment
                break
        
        return specs
    
    def analyze_template_quality(self, template: Dict[str, str], language: str) -> Dict[str, Any]:
        """
        Analyze the quality of a generated template
        """
        analysis = {
            'file_count': len(template),
            'code_files': 0,
            'config_files': 0,
            'doc_files': 0,
            'has_readme': 'README.md' in template,
            'has_gitignore': '.gitignore' in template,
            'has_requirements': any('requirements' in f.lower() or 'package.json' in f for f in template),
            'issues': [],
            'score': 0
        }
        
        for file_path, content in template.items():
            if self.template_service._is_code_file(file_path):
                analysis['code_files'] += 1
                
                # Check code quality
                if not self.template_service._has_error_handling(content, language):
                    analysis['issues'].append(f"Missing error handling in {file_path}")
                
                if not self.template_service._has_basic_structure(content, language):
                    analysis['issues'].append(f"Poor structure in {file_path}")
            
            elif any(ext in file_path for ext in ['.json', '.yaml', '.yml', '.toml', '.ini']):
                analysis['config_files'] += 1
            elif any(ext in file_path for ext in ['.md', '.txt', '.rst']):
                analysis['doc_files'] += 1
        
        # Calculate quality score
        analysis['score'] = self._calculate_template_score(analysis)
        
        return analysis
    
    def _calculate_template_score(self, analysis: Dict[str, Any]) -> int:
        """Calculate template quality score (0-100)"""
        score = 0
        
        if analysis['file_count'] >= 3:
            score += 20
        if analysis['code_files'] >= 1:
            score += 20
        if analysis['has_readme']:
            score += 20
        if analysis['has_gitignore']:
            score += 20
        if analysis['has_requirements']:
            score += 20
        
        # Deduct for issues
        score -= min(len(analysis['issues']) * 5, 40)
        
        return max(0, min(100, score))
