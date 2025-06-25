from collections import Counter
import re
from sklearn.feature_extraction.text import TfidfVectorizer

# Utility to extract keywords from a list of texts

def extract_top_keywords(texts, top_n=10):
    # Combine all texts
    combined_text = ' '.join(texts)
    # Remove non-alphabetic characters
    combined_text = re.sub(r'[^a-zA-Z ]', ' ', combined_text)
    # Tokenize and lower
    words = combined_text.lower().split()
    # Remove stopwords (simple set, can be improved)
    stopwords = set([
        'the', 'and', 'to', 'of', 'a', 'in', 'for', 'is', 'on', 'that', 'with', 'as', 'are', 'it', 'this', 'was', 'at', 'by', 'an', 'be', 'from', 'or', 'has', 'have', 'not', 'but', 'they', 'you', 'we', 'can', 'all', 'will', 'if', 'so', 'do', 'about', 'more', 'what', 'when', 'which', 'their', 'one', 'our', 'how', 'who', 'your', 'out', 'use', 'get', 'just', 'like', 'also', 'my', 'there', 'should', 'had', 'were', 'them', 'been', 'than', 'some', 'no', 'into', 'other', 'up', 'would', 'could', 'any', 'because', 'very', 'over', 'after', 'most', 'these', 'me', 'he', 'she', 'his', 'her', 'its', 'i', 'you', 'us', 'am', 'im', 'did', 'does', 'doing', 'done', 'where', 'why', 'yes', 'too', 'still', 'even', 'see', 'go', 'going', 'back', 'off', 'new', 'now', 'then', 'here', 'make', 'made', 'much', 'many', 'own', 'want', 'needs', 'need', 'every', 'each', 'per', 'such', 'being', 'through', 'during', 'before', 'while', 'both', 'between', 'under', 'again', 'same', 'few', 'those', 'may', 'might', 'must', 'shall', 'upon', 'without', 'within', 'among', 'against', 'around', 'across', 'towards', 'toward', 'since', 'until', 'whose', 'whom', 'which', 'who', 'whom', 'where', 'when', 'why', 'how', 'what', 'that', 'this', 'these', 'those', 'it', 'they', 'he', 'she', 'we', 'you', 'i', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'their', 'our', 'mine', 'yours', 'hers', 'theirs', 'ours', 'myself', 'yourself', 'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves', 'own', 'same', 'such', 'than', 'too', 'very', 'can', 'will', 'just', 'don', 'should', 'now'])
    filtered_words = [w for w in words if w not in stopwords and len(w) > 2]
    # Count frequency
    freq = Counter(filtered_words)
    # Return top N
    return [w for w, _ in freq.most_common(top_n)]
