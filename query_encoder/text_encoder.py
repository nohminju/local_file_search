import torch
import open_clip


class KoreanTextEncoder:
    def __init__(self, model=None, tokenizer=None):
        # GPU 사용 가능 여부 확인 (없으면 CPU 사용)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # 외부에서 이미 불러온 모델이 있으면 재사용하고, 없으면 새로 로드
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
            
        # 학습이 아닌 추론(검색) 모드로 설정
        self.model.eval()

    def encode_text(self, text_list):
        # 문장 1개(str)만 들어오면 리스트로 감싸서 항상 2차원 (N, 512) 형태 유지
        if type(text_list) == str:
            text_list = [text_list]

        # 텍스트를 모델 입력용 숫자 토큰으로 변환
        tokens = self.tokenizer(text_list).to(self.device)

        # 기울기 계산을 꺼서 불필요한 연산 방지 및 속도 향상
        with torch.no_grad():
            text_features = self.model.encode_text(tokens)
            # 코사인 유사도 계산을 위해 벡터의 크기를 1로 맞추는 정규화(L2 Norm) 수행
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        # FAISS 인덱스에 넣을 수 있도록 float32 타입의 넘파이 배열로 반환
        return text_features.cpu().numpy().astype("float32")
