import spacy
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.translate.bleu_score import sentence_bleu
from language_tool_python import LanguageTool
import warnings

warnings.filterwarnings("ignore")

nlp = spacy.load("en_core_web_sm")

language_tool = LanguageTool('en-US')

class ShortAnswerGrader:
    def __init__(self):
        pass

    def compute_cosine_similarity(self, reference_answer, actual_answer):
        vectorizer = CountVectorizer().fit_transform([reference_answer, actual_answer])
        vectors = vectorizer.toarray()
        similarity_score = cosine_similarity(vectors[0].reshape(1, -1), vectors[1].reshape(1, -1))[0][0]
        return similarity_score

    def compute_ner_matching_score(self, reference_answer, actual_answer):
        reference_entities = set([ent.text.lower() for ent in nlp(reference_answer).ents])
        actual_entities = set([ent.text.lower() for ent in nlp(actual_answer).ents])
        if len(reference_entities) == 0 or len(actual_entities) == 0:
            return 0.0
        matching_entities = reference_entities.intersection(actual_entities)
        ner_score = len(matching_entities) / max(len(reference_entities), len(actual_entities))
        return ner_score

    def compute_grammar_spelling_score(self, actual_answer):
        matches = language_tool.check(actual_answer)
        num_errors = len(matches)
        grammar_spelling_score = 1 - (num_errors / len(actual_answer.split()))
        return grammar_spelling_score

    def compute_semantic_similarity(self, reference_answer, actual_answer):
        reference_doc = nlp(reference_answer)
        actual_doc = nlp(actual_answer)
        similarity_score = reference_doc.similarity(actual_doc)
        return similarity_score

    def compute_syntactic_analysis_score(self, actual_answer):
        doc = nlp(actual_answer)
        num_clauses = len([token for token in doc if token.dep_ == 'ROOT'])
        syntactic_analysis_score = 1 - (num_clauses / len(doc))
        return syntactic_analysis_score

    def compute_bleu_score(self, reference_answer, actual_answer):
        reference_tokens = reference_answer.split()
        actual_tokens = actual_answer.split()
        bleu_score = sentence_bleu([reference_tokens], actual_tokens)
        return bleu_score

    def calculate(self, reference_answer, actual_answer):
        cosine_similarity_score = self.compute_cosine_similarity(reference_answer, actual_answer)
        ner_matching_score = self.compute_ner_matching_score(reference_answer, actual_answer)
        grammar_spelling_score = self.compute_grammar_spelling_score(actual_answer)
        semantic_similarity_score = self.compute_semantic_similarity(reference_answer, actual_answer)
        syntactic_analysis_score = self.compute_syntactic_analysis_score(actual_answer)
        bleu_score = self.compute_bleu_score(reference_answer, actual_answer)

        # Define weights for each metric
        weights = {
            "cosine_similarity": 0.25,
            "ner_matching": 0.15,
            "grammar_spelling": 0.1,
            "semantic_similarity": 0.2,
            "syntactic_analysis": 0.1,
            "bleu_score": 0.15
        }

        # Calculate overall score
        overall_score = (
            weights["cosine_similarity"] * cosine_similarity_score +
            weights["ner_matching"] * ner_matching_score +
            weights["grammar_spelling"] * grammar_spelling_score +
            weights["semantic_similarity"] * semantic_similarity_score +
            weights["syntactic_analysis"] * syntactic_analysis_score +
            weights["bleu_score"] * bleu_score
        )

        if(overall_score>0.59):
            return 1
        elif(overall_score>=0.25 and overall_score<=0.59):
            return 0.5
        return 0
