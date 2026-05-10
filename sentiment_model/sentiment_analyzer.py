import json
import os
import torch
from transformers import TextClassificationPipeline
from transformers import AutoModelForSequenceClassification
from transformers import BertTokenizerFast

class SentimentAnalyzer:
    def __init__(self, model_name="yiyanghkust/finbert-tone-chinese"):
        # 檢查是否有顯卡可用
        self.device = 0 if torch.cuda.is_available() else -1

        # 載入預訓練模型權重與分詞器
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.tokenizer = BertTokenizerFast.from_pretrained(model_name)

        self.pipeline = TextClassificationPipeline(
            model=self.model,
            tokenizer=self.tokenizer,
            top_k=None, # 確保回傳所有標籤
            device=self.device
        )

    def analyze_text(self, text):
        """
        純粹的分析函數：輸入字串，回傳三個情緒標籤的機率與加權綜合分數
        """
        # 防呆機制
        if not text or not isinstance(text, str):
            return {"Positive": 0.0, "Neutral": 0.0, "Negative": 0.0, "Composite_Score": 0.0}

        # 截斷前 512 個字以符合 BERT 限制
        text_content = text[:512]

        # 取得分析結果
        raw_results = self.pipeline(text_content)
        
        # 安全機制：處理 pipeline 雙層 list 的狀況
        if isinstance(raw_results[0], list):
            raw_results = raw_results[0]
        
        # 1. 整理成乾淨的機率字典
        detailed_scores = {}
        for item in raw_results:
            detailed_scores[item['label']] = item['score'] # 先保留原始精度做計算

        # 2. 計算權重綜合分數 (Composite Score)
        # Positive * 1 + Neutral * 0 + Negative * -1
        composite_score = (detailed_scores.get('Positive', 0) * 1.0) + \
                          (detailed_scores.get('Neutral', 0) * 0.0) + \
                          (detailed_scores.get('Negative', 0) * -1.0)

        # 3. 四捨五入美化所有數值，準備輸出
        for key in detailed_scores:
            detailed_scores[key] = round(detailed_scores[key], 4)
            
        detailed_scores["Composite_Score"] = round(composite_score, 4)

        return detailed_scores
    
# --- 測試區塊 ---
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()

    # 模擬從爬蟲抓下來的一段純文字
    sample_text = "他强调，现阶段「记忆体族群」已成为最强主流，台股相关个股补涨力道不容小觑，不过十铨4月营收减59%，投资人需留意股价下修风险。美股指标指数创历史新高，特别是费城半导体指数8日大涨5.5%，为台股下周走势注入强心针。"

    print("--- 開始測試純文字分析 ---")
    result = analyzer.analyze_text(sample_text)

    # 印出結果
    print(json.dumps(result, ensure_ascii=False, indent=4))