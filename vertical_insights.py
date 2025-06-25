import os
import json
from datetime import datetime
from langchain_ollama import OllamaLLM

# Configure Ollama
llm = OllamaLLM(
    model="mistral:7b-instruct-q4_0",
    temperature=0.7,
    num_ctx=4096,
    num_thread=4,
    repeat_penalty=1.1,
    top_k=40,
    top_p=0.9
)

class VerticalInsights:
    """Provides industry-specific insights for different verticals"""
    
    # Define industry verticals and their specific attributes
    VERTICALS = {
        "fintech": {
            "name": "Financial Technology",
            "keywords": ["banking", "payment", "finance", "loan", "credit", "insurance", "invest"],
            "metrics": ["user acquisition cost", "lifetime value", "churn rate", "transaction volume"],
            "regulations": ["PSD2", "GDPR", "KYC", "AML", "PCI DSS"]
        },
        "healthcare": {
            "name": "Healthcare & Medical",
            "keywords": ["patient", "doctor", "hospital", "clinic", "medical", "health", "wellness"],
            "metrics": ["patient acquisition cost", "readmission rate", "treatment efficacy"],
            "regulations": ["HIPAA", "FDA", "GDPR", "CCPA"]
        },
        "ecommerce": {
            "name": "E-Commerce & Retail",
            "keywords": ["shop", "retail", "store", "product", "purchase", "buy", "customer"],
            "metrics": ["conversion rate", "cart abandonment", "average order value", "customer lifetime value"],
            "regulations": ["GDPR", "CCPA", "PCI DSS"]
        },
        "saas": {
            "name": "Software as a Service",
            "keywords": ["subscription", "cloud", "platform", "software", "service", "user", "enterprise"],
            "metrics": ["MRR", "ARR", "CAC", "LTV", "churn rate", "NPS"],
            "regulations": ["GDPR", "CCPA", "SOC 2"]
        },
        "edtech": {
            "name": "Education Technology",
            "keywords": ["learn", "student", "teacher", "school", "education", "course", "training"],
            "metrics": ["completion rate", "engagement", "knowledge retention", "student satisfaction"],
            "regulations": ["FERPA", "COPPA", "GDPR"]
        }
    }
    
    def __init__(self):
        pass
        
    def detect_vertical(self, keyword, content):
        """Detect the most relevant vertical for a query"""
        # Simple keyword matching for vertical detection
        keyword_lower = keyword.lower()
        content_lower = content.lower() if content else ""
        
        scores = {}
        for vertical, data in self.VERTICALS.items():
            score = 0
            # Check main keyword
            for kw in data["keywords"]:
                if kw in keyword_lower:
                    score += 10
                if content_lower and kw in content_lower:
                    score += 1
            scores[vertical] = score
        
        # Get vertical with highest score
        best_match = max(scores.items(), key=lambda x: x[1])
        if best_match[1] > 0:
            return best_match[0]
        
        # If no clear match, use AI to detect
        prompt = f"""
        Based on this keyword and content, which industry vertical is most relevant?
        Options: fintech, healthcare, ecommerce, saas, edtech
        
        Keyword: {keyword}
        Content snippet: {content[:500] if content else ""}
        
        Return only the single most relevant vertical name from the options.
        """
        
        try:
            response = llm.invoke(prompt)
            detected = response.strip().lower()
            if detected in self.VERTICALS:
                return detected
        except Exception:
            pass
            
        # Default to SaaS if no match
        return "saas"
    
    def get_vertical_insights(self, vertical, keyword, content):
        """Get industry-specific insights for a vertical"""
        if vertical not in self.VERTICALS:
            vertical = self.detect_vertical(keyword, content)
            
        vertical_data = self.VERTICALS[vertical]
        
        # Create prompt for vertical-specific analysis
        prompt = f"""
        You are an expert market analyst specializing in {vertical_data['name']}.
        
        Analyze this content related to the keyword "{keyword}" from a {vertical_data['name']} industry perspective.
        
        Content to analyze:
        {content[:2000] if content else "No content provided"}
        
        Provide insights in these specific areas:
        
        1. Industry-Specific Pain Points:
           - Identify pain points specific to the {vertical_data['name']} industry
           - Rate severity on scale of 1-10
           - Note if these are emerging or established problems
        
        2. Regulatory & Compliance Considerations:
           - Identify any relevant regulatory concerns (consider: {', '.join(vertical_data['regulations'])})
           - Note compliance challenges that create opportunities
        
        3. Key Performance Indicators:
           - Which metrics matter most for solutions in this space (consider: {', '.join(vertical_data['metrics'])})
           - How solutions should measure success
        
        4. Competitive Landscape:
           - Identify key players in this specific vertical
           - Note gaps in their offerings
        
        5. Vertical-Specific Opportunities:
           - Suggest 2-3 specific product ideas tailored to {vertical_data['name']}
           - For each, note target user, core value proposition, and potential go-to-market strategy
        
        Format your response with clear headings and bullet points. Be specific to {vertical_data['name']} industry.
        """
        
        try:
            response = llm.invoke(prompt)
            return {
                "vertical": vertical,
                "vertical_name": vertical_data["name"],
                "insights": response.strip()
            }
        except Exception as e:
            return {
                "vertical": vertical,
                "vertical_name": vertical_data["name"],
                "insights": f"Error generating insights: {str(e)}",
                "error": True
            }
    
    def get_vertical_context(self, vertical):
        """Get context information for a vertical"""
        if vertical not in self.VERTICALS:
            return "General business context"
        
        vertical_data = self.VERTICALS[vertical]
        return f"{vertical_data['name']} industry with focus on {', '.join(vertical_data['keywords'][:3])} and metrics like {', '.join(vertical_data['metrics'][:2])}"
    
    def get_all_verticals(self):
        """Get list of all supported verticals"""
        return {k: v["name"] for k, v in self.VERTICALS.items()}

# Singleton instance
vertical_insights = VerticalInsights()