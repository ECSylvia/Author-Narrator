import os
import re

class Chapter:
    def __init__(self, title, content, order):
        self.title = title
        self.content = content
        self.order = order

    def __repr__(self):
        return f"<Chapter {self.order}: {self.title}>"

class ManuscriptParser:
    @staticmethod
    def parse_file(file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        if ext == '.md':
            return ManuscriptParser._parse_markdown(content)
        elif ext == '.txt':
            return ManuscriptParser._parse_text(content)
        else:
            # Fallback: Treat whole file as one chapter
            return [Chapter("Full Text", content, 1)]

    @staticmethod
    def _parse_markdown(content):
        # Split by Headers (# Chapter 1 or ## Chapter 1)
        # Regex looks for lines starting with #
        
        lines = content.split('\n')
        chapters = []
        current_title = "Introduction"
        current_content = []
        order = 1
        
        for line in lines:
            # Check for header
            if line.startswith('#'):
                # Save previous chapter if it has content
                if current_content:
                    chapters.append(Chapter(current_title, '\n'.join(current_content).strip(), order))
                    order += 1
                    current_content = []
                
                # New Title (strip # and cleanup)
                current_title = line.lstrip('#').strip()
            else:
                current_content.append(line)
                
        # Save last chapter
        if current_content or current_title:
             chapters.append(Chapter(current_title, '\n'.join(current_content).strip(), order))
             
        return chapters

    _HEADING_RE = re.compile(
        r'^\s*(?:chapter\s+[\w\-]+|prologue|epilogue)(?:\s*[-–—:].+)?$',
        re.IGNORECASE,
    )

    @staticmethod
    def _parse_text(content):
        lines = content.split('\n')
        chapters = []
        current_title = "Beginning"
        current_content = []
        order = 1

        for line in lines:
            if ManuscriptParser._HEADING_RE.match(line):
                if current_content:
                    chapters.append(Chapter(current_title, '\n'.join(current_content).strip(), order))
                    order += 1
                    current_content = []

                current_title = line.strip()
            else:
                current_content.append(line)

        if current_content:
            chapters.append(Chapter(current_title, '\n'.join(current_content).strip(), order))

        return chapters
