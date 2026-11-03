import torch
import open_clip

class KoreanTextEncoder:
    def __init__(self, model=None, tokenizer=None):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 외부에서 공통 모델을 넘겨주면 사용하고, 없으면 직접 로딩
        if model is not None and tokenizer is not None:
            self.model = model
            self.tokenizer = tokenizer
        else:
            self.model, _, _ = open_clip.create_model_and_transforms(
                'xlm-roberta-base-ViT-B-32', 
                pretrained='laion5b_s13b_b90k'
            )
            self.model.to(self.device)
            self.tokenizer = open_clip.get_tokenizer('xlm-roberta-base-ViT-B-32')
            
        self.model.eval()

    def encode_text(self, text_list):
        # 단일 문자열이 들어오면 리스트로 변환
        if isinstance(text_list, str):
            text_list = [text_list]

        tokens = self.tokenizer(text_list).to(self.device)

        with torch.no_grad():
            text_features = self.model.encode_text(tokens)
            # 코사인 유사도 계산을 위한 벡터 정규화
            text_features /= text_features.norm(dim=-1, keepdim=True)

        return text_features.cpu().numpy()
