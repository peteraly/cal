"""
Advanced Event Extraction using spaCy and NLTK
This module provides sophisticated NLP-based event extraction capabilities.
"""

import re
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.chunk import ne_chunk
    from nltk.tag import pos_tag
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

class AdvancedEventExtractor:
    """
    Advanced event extraction using multiple NLP techniques.
    """
    
    def __init__(self):
        self.nlp = None
        self.event_triggers = {
            'performance': ['concert', 'show', 'performance', 'play', 'musical', 'dance', 'theater', 'theatre'],
            'social': ['party', 'gala', 'celebration', 'festival', 'fair', 'carnival', 'parade'],
            'educational': ['workshop', 'class', 'seminar', 'lecture', 'talk', 'presentation', 'conference'],
            'commercial': ['sale', 'market', 'auction', 'fundraiser', 'opening', 'launch', 'premiere'],
            'recreational': ['tour', 'walk', 'run', 'race', 'game', 'match', 'tasting', 'screening'],
            'cultural': ['exhibition', 'museum', 'gallery', 'library', 'ceremony', 'film', 'movie']
        }
        
        # Initialize spaCy if available
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                print("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
                SPACY_AVAILABLE = False
        
        # Download NLTK data if available
        if NLTK_AVAILABLE:
            try:
                nltk.data.find('tokenizers/punkt')
                nltk.data.find('taggers/averaged_perceptron_tagger')
                nltk.data.find('chunkers/maxent_ne_chunker')
            except LookupError:
                print("NLTK data not found. Run: nltk.download('punkt'), nltk.download('averaged_perceptron_tagger'), nltk.download('maxent_ne_chunker')")
                NLTK_AVAILABLE = False
    
    def extract_events_spacy(self, text: str) -> List[Dict]:
        """
        Extract events using spaCy NLP processing.
        """
        if not SPACY_AVAILABLE or not self.nlp:
            return []
        
        events = []
        doc = self.nlp(text)
        
        # Find sentences with event triggers
        for sent in doc.sents:
            event_info = self._analyze_sentence_spacy(sent)
            if event_info:
                events.append(event_info)
        
        return events
    
    def _analyze_sentence_spacy(self, sentence) -> Optional[Dict]:
        """
        Analyze a sentence for event information using spaCy.
        """
        event_info = {
            'title': '',
            'date': None,
            'time': None,
            'location': None,
            'description': sentence.text.strip(),
            'price_info': None
        }
        
        # Check for event triggers
        has_event_trigger = False
        for token in sentence:
            if any(trigger in token.text.lower() for triggers in self.event_triggers.values() for trigger in triggers):
                has_event_trigger = True
                break
        
        if not has_event_trigger:
            return None
        
        # Extract named entities
        for ent in sentence.ents:
            if ent.label_ == "DATE":
                event_info['date'] = ent.text
            elif ent.label_ == "TIME":
                event_info['time'] = ent.text
            elif ent.label_ in ["GPE", "LOC", "ORG", "FAC"]:
                if not event_info['location']:
                    event_info['location'] = ent.text
        
        # Extract title (first noun phrase or first few words)
        for token in sentence:
            if token.pos_ in ['NOUN', 'PROPN'] and not event_info['title']:
                event_info['title'] = token.text
                break
        
        # Extract price information
        price_pattern = r'\$\d+(?:\.\d{2})?|\b(?:free|Free|FREE)\b'
        price_match = re.search(price_pattern, sentence.text)
        if price_match:
            event_info['price_info'] = price_match.group()
        
        return event_info
    
    def extract_events_nltk(self, text: str) -> List[Dict]:
        """
        Extract events using NLTK processing.
        """
        if not NLTK_AVAILABLE:
            return []
        
        events = []
        sentences = sent_tokenize(text)
        
        for sentence in sentences:
            event_info = self._analyze_sentence_nltk(sentence)
            if event_info:
                events.append(event_info)
        
        return events
    
    def _analyze_sentence_nltk(self, sentence: str) -> Optional[Dict]:
        """
        Analyze a sentence for event information using NLTK.
        """
        event_info = {
            'title': '',
            'date': None,
            'time': None,
            'location': None,
            'description': sentence.strip(),
            'price_info': None
        }
        
        # Tokenize and tag
        tokens = word_tokenize(sentence)
        pos_tags = pos_tag(tokens)
        
        # Check for event triggers
        has_event_trigger = False
        for word, tag in pos_tags:
            if any(trigger in word.lower() for triggers in self.event_triggers.values() for trigger in triggers):
                has_event_trigger = True
                break
        
        if not has_event_trigger:
            return None
        
        # Named entity recognition
        ne_tree = ne_chunk(pos_tags)
        
        for subtree in ne_tree:
            if hasattr(subtree, 'label'):
                if subtree.label() in ['GPE', 'LOCATION', 'ORGANIZATION', 'FACILITY']:
                    if not event_info['location']:
                        event_info['location'] = ' '.join([token for token, pos in subtree.leaves()])
        
        # Extract title (first noun)
        for word, tag in pos_tags:
            if tag in ['NN', 'NNP', 'NNS', 'NNPS'] and not event_info['title']:
                event_info['title'] = word
                break
        
        # Extract price information
        price_pattern = r'\$\d+(?:\.\d{2})?|\b(?:free|Free|FREE)\b'
        price_match = re.search(price_pattern, sentence)
        if price_match:
            event_info['price_info'] = price_match.group()
        
        return event_info
    
    def extract_events_hybrid(self, text: str) -> List[Dict]:
        """
        Extract events using a hybrid approach combining multiple methods.
        """
        events = []
        
        # Try spaCy first
        if SPACY_AVAILABLE:
            spacy_events = self.extract_events_spacy(text)
            events.extend(spacy_events)
        
        # Try NLTK if spaCy didn't find enough events
        if len(events) < 2 and NLTK_AVAILABLE:
            nltk_events = self.extract_events_nltk(text)
            events.extend(nltk_events)
        
        # Remove duplicates based on description similarity
        unique_events = []
        for event in events:
            is_duplicate = False
            for unique_event in unique_events:
                if self._events_similar(event, unique_event):
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_events.append(event)
        
        return unique_events
    
    def _events_similar(self, event1: Dict, event2: Dict, threshold: float = 0.8) -> bool:
        """
        Check if two events are similar based on their descriptions.
        """
        desc1 = event1.get('description', '').lower()
        desc2 = event2.get('description', '').lower()
        
        # Simple similarity check based on common words
        words1 = set(desc1.split())
        words2 = set(desc2.split())
        
        if not words1 or not words2:
            return False
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        similarity = len(intersection) / len(union)
        return similarity >= threshold

# Global instance
advanced_extractor = AdvancedEventExtractor()

def extract_events_advanced(text: str) -> List[Dict]:
    """
    Main function to extract events using advanced NLP techniques.
    """
    return advanced_extractor.extract_events_hybrid(text)
