import re
import json
import random
from typing import Dict, Any, List
from groq import Groq
from config import Config
from logs import logger


try:
    import language_tool_python
    tool = language_tool_python.LanguageTool('en-US')
except ImportError:
    tool = None
    logger.warning("language-tool-python not found. Grammar scoring will be mocked or limited.")
except Exception as e:
    tool = None
    logger.warning(f"LanguageTool failed to init: {e}")

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    analyzer = SentimentIntensityAnalyzer()
except ImportError:
    analyzer = None
    logger.warning("vaderSentiment not found. Sentiment scoring will be limited.")

class ScoringEngine:
    def __init__(self):
        self.api_keys = Config.GROQ_API_KEYS
        self.current_key_index = 0

    def _get_client(self):
        if not self.api_keys:
            raise ValueError("No Groq API keys found in environment variables.")

        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return Groq(api_key=key)
    def _call_llm(self, transcript: str) -> Dict[str, Any]:
        prompt = f"{Config.SYSTEM_PROMPT}\n\nTranscript:\n{transcript}"
        
        max_retries = len(self.api_keys)
        last_error = None
        
        for attempt in range(max_retries):
            try:
                client = self._get_client()
                logger.info(f"Sending request to Groq LLM with model: {Config.MODEL_NAME} (attempt {attempt + 1}/{max_retries})")
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    model=Config.MODEL_NAME,
                    response_format={"type": "json_object"}
                )
                
                content = chat_completion.choices[0].message.content
                logger.info(f"Received response from LLM: {content}")
                return json.loads(content)
            except Exception as e:
                last_error = e
                logger.warning(f"LLM Call failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying with next API key...")
        
        logger.error(f"All LLM API keys failed. Last error: {last_error}")
        
        return {
            "Salutation Level": "Normal",
            "Keyword Presence": [],
            "Flow": "Order Not followed",
            "Engagement": "Neutral"
        }


    def calculate_rule_based(self, text: str, duration_sec: int = None) -> Dict[str, Any]:
        words = re.findall(r'\b\w+\b', text.lower())
        word_count = len(words)
        if word_count == 0:
            return {}


        wpm = 0
        speech_score = 0
        speech_feedback = "N/A"
        if duration_sec and duration_sec > 0:
            wpm = (word_count / duration_sec) * 60
            if wpm > Config.SPEECH_RATE_THRESHOLDS["too_fast"]:
                speech_score = 2
                speech_feedback = "Too Fast"
            elif Config.SPEECH_RATE_THRESHOLDS["fast_min"] <= wpm <= Config.SPEECH_RATE_THRESHOLDS["too_fast"] - 1:
                speech_score = 6
                speech_feedback = "Fast"
            elif Config.SPEECH_RATE_THRESHOLDS["ideal_min"] <= wpm < Config.SPEECH_RATE_THRESHOLDS["fast_min"]:
                speech_score = 10
                speech_feedback = "Ideal"
            elif Config.SPEECH_RATE_THRESHOLDS["slow_min"] <= wpm < Config.SPEECH_RATE_THRESHOLDS["ideal_min"]:
                speech_score = 6
                speech_feedback = "Slow"
            else:
                speech_score = 2
                speech_feedback = "Too Slow"
        else:

            speech_score = 10
            speech_feedback = "Duration not provided (Assumed Ideal)"


        grammar_score = 10
        errors = 0
        if tool:
            matches = tool.check(text)
            errors = len(matches)
            raw_score = 1 - min((errors / word_count * 100) / 10, 1)
            
            if raw_score >= Config.GRAMMAR_THRESHOLDS["excellent"]: grammar_score = 10
            elif raw_score >= Config.GRAMMAR_THRESHOLDS["good"]: grammar_score = 8
            elif raw_score >= Config.GRAMMAR_THRESHOLDS["average"]: grammar_score = 6
            elif raw_score >= Config.GRAMMAR_THRESHOLDS["poor"]: grammar_score = 4
            else: grammar_score = 2
        

        unique_words = len(set(words))
        ttr = unique_words / word_count if word_count > 0 else 0
        vocab_score = 0
        if ttr >= Config.VOCAB_THRESHOLDS["excellent"]: vocab_score = 10
        elif ttr >= Config.VOCAB_THRESHOLDS["good"]: vocab_score = 8
        elif ttr >= Config.VOCAB_THRESHOLDS["average"]: vocab_score = 6
        elif ttr >= Config.VOCAB_THRESHOLDS["poor"]: vocab_score = 4
        else: vocab_score = 2


        filler_count = sum(1 for w in words if w in Config.FILLER_WORDS)
        filler_rate = (filler_count / word_count) * 100 if word_count > 0 else 0
        clarity_score = 0
        if filler_rate <= Config.FILLER_THRESHOLDS["excellent"]: clarity_score = 15
        elif filler_rate <= Config.FILLER_THRESHOLDS["good"]: clarity_score = 12
        elif filler_rate <= Config.FILLER_THRESHOLDS["average"]: clarity_score = 9
        elif filler_rate <= Config.FILLER_THRESHOLDS["poor"]: clarity_score = 6
        else: clarity_score = 3


        sentiment_score = 0
        pos_score = 0
        if analyzer:
            vs = analyzer.polarity_scores(text)

            compound_norm = (vs['compound'] + 1) / 2
            pos_score = compound_norm
            
            if pos_score >= Config.ENGAGEMENT_THRESHOLDS["excellent"]: sentiment_score = 15
            elif pos_score >= Config.ENGAGEMENT_THRESHOLDS["good"]: sentiment_score = 12
            elif pos_score >= Config.ENGAGEMENT_THRESHOLDS["average"]: sentiment_score = 9
            elif pos_score >= Config.ENGAGEMENT_THRESHOLDS["poor"]: sentiment_score = 6
            else: sentiment_score = 3
        else:
            sentiment_score = 15 

        return {
            "word_count": word_count,
            "speech_rate": {"wpm": wpm, "score": speech_score, "feedback": speech_feedback},
            "grammar": {"errors": errors, "score": grammar_score},
            "vocabulary": {"ttr": ttr, "score": vocab_score},
            "clarity": {"filler_rate": filler_rate, "score": clarity_score, "count": filler_count},
            "engagement_rule": {"pos_score": pos_score, "score": sentiment_score}
        }

    def _flatten_list(self, data):
        """Recursively flatten nested lists and extract strings."""
        result = []
        if isinstance(data, str):
            return [data]
        elif isinstance(data, (int, float)):
            return [str(data)]
        elif isinstance(data, dict):
            for v in data.values():
                result.extend(self._flatten_list(v))
        elif isinstance(data, list):
            for item in data:
                result.extend(self._flatten_list(item))
        return result

    def score_transcript(self, transcript: str, duration: int = None):

        rb_metrics = self.calculate_rule_based(transcript, duration)
        

        llm_result = self._call_llm(transcript)
        

        breakdown = []


        sal_data = llm_result.get("Salutation Level", llm_result.get("salutation_level", "Normal"))
        sal_level = "Normal"
        sal_score = 2
        
        if isinstance(sal_data, dict):
            sal_level = sal_data.get("value", sal_data.get("description", "Normal"))
            if "score" in sal_data:
                sal_score = int(sal_data["score"])
            else:
                salutation_map = {"No Salutation": 0, "Normal": 2, "Good": 4, "Excellent": 5}
                sal_score = salutation_map.get(sal_level, 2)
        elif isinstance(sal_data, (int, float)):
            sal_score = int(sal_data)
            score_to_level = {0: "No Salutation", 2: "Normal", 4: "Good", 5: "Excellent"}
            sal_level = score_to_level.get(sal_score, "Normal")
        else:
            sal_level = str(sal_data)
            salutation_map = {"No Salutation": 0, "Normal": 2, "Good": 4, "Excellent": 5}
            sal_score = salutation_map.get(sal_level, 2)
        

        found_keywords_raw = llm_result.get("Keyword Presence", llm_result.get("keyword_presence", []))
        found_keywords = self._flatten_list(found_keywords_raw)
        
        found_lower = []
        try:
            found_lower = [str(k).lower().strip() for k in found_keywords if k is not None and str(k).strip()]
        except Exception as e:
            logger.error(f"Error normalizing keywords: {e}, Raw: {found_keywords_raw}")
            found_lower = []

        logger.info(f"Normalized keywords from LLM: {found_lower}")
        
        mh_count = 0
        for category, keywords in Config.MUST_HAVE_KEYWORDS.items():
            if any(kw in k for k in found_lower for kw in keywords):
                mh_count += 1
            elif any(category in k for k in found_lower): 
                mh_count += 1
                
        mh_score = mh_count * 4
        
        gh_count = 0
        for category, keywords in Config.GOOD_TO_HAVE_KEYWORDS.items():
            if any(kw in k for k in found_lower for kw in keywords):
                gh_count += 1
            elif any(category in k for k in found_lower):
                gh_count += 1
                
        gh_score = gh_count * 2
        
        keyword_score = min(mh_score + gh_score, 30)
        logger.info(f"Keyword Score: {keyword_score} (MH: {mh_count}, GH: {gh_count})")


        flow_data = llm_result.get("Flow", llm_result.get("flow", "Order Not followed"))
        flow_status = "Order Not followed"
        flow_score = 0
        
        if isinstance(flow_data, dict):
            flow_status = str(flow_data.get("status", flow_data.get("description", "Order Not followed")))
            if "order_followed" in flow_data:
                flow_score = 5 if flow_data["order_followed"] else 0
            elif "score" in flow_data:
                flow_score = int(flow_data["score"])
        elif isinstance(flow_data, (int, float)):
            flow_score = int(flow_data)
            flow_status = "Order followed" if flow_score >= 5 else "Order Not followed"
        elif isinstance(flow_data, bool):
            flow_score = 5 if flow_data else 0
            flow_status = "Order followed" if flow_data else "Order Not followed"
        else:
            flow_status = str(flow_data)
        
        flow_status_lower = flow_status.lower()
        if "order followed" in flow_status_lower or "5" in flow_status_lower or "yes" in flow_status_lower or "true" in flow_status_lower:
            flow_score = 5

        content_score = sal_score + keyword_score + flow_score
        breakdown.append({"criterion": "Content & Structure", "score": content_score, "max": 40, "feedback": f"Salutation: {sal_level}, Keywords found: {len(found_lower)} items, Flow: {flow_status}"})


        breakdown.append({"criterion": "Speech Rate", "score": rb_metrics['speech_rate']['score'], "max": 10, "feedback": f"{rb_metrics['speech_rate']['wpm']:.0f} WPM ({rb_metrics['speech_rate']['feedback']})"})


        lg_score = rb_metrics['grammar']['score'] + rb_metrics['vocabulary']['score']
        breakdown.append({"criterion": "Language & Grammar", "score": lg_score, "max": 20, "feedback": f"Grammar Score: {rb_metrics['grammar']['score']}/10, Vocabulary Score: {rb_metrics['vocabulary']['score']}/10 (TTR: {rb_metrics['vocabulary']['ttr']:.2f})"})


        breakdown.append({"criterion": "Clarity", "score": rb_metrics['clarity']['score'], "max": 15, "feedback": f"Filler Word Rate: {rb_metrics['clarity']['filler_rate']:.1f}%"})


        engagement_data = llm_result.get("Engagement", llm_result.get("Engagement/Sentiment", llm_result.get("engagement_sentiment", "Neutral")))
        llm_sentiment = "Neutral"
        
        if isinstance(engagement_data, dict):
            llm_sentiment = str(engagement_data.get("tone", engagement_data.get("description", "Neutral")))
        else:
            llm_sentiment = str(engagement_data)
            
        eng_score = rb_metrics['engagement_rule']['score']
        breakdown.append({"criterion": "Engagement", "score": eng_score, "max": 15, "feedback": f"Sentiment: {llm_sentiment} (Score based on positivity probability)"})

        total_score = content_score + rb_metrics['speech_rate']['score'] + lg_score + rb_metrics['clarity']['score'] + eng_score

        return {
            "overall_score": total_score,
            "breakdown": breakdown,
            "transcript_stats": {
                "word_count": rb_metrics['word_count'],
                "duration": duration
            }
        }
