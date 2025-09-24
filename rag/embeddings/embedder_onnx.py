import onnxruntime as ort
from transformers import AutoTokenizer
import os


class ONNXEmbedder:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        model_path = os.path.join(
            os.path.dirname(__file__), "..", "models", "model.onnx"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Configure session options to avoid CPU affinity issues
        options = ort.SessionOptions()
        options.inter_op_num_threads = 1
        options.intra_op_num_threads = 1

        self.session = ort.InferenceSession(model_path, sess_options=options)

    def embed(self, text: str) -> list:
        tokens = self.tokenizer(
            text, return_tensors="np", padding=True, truncation=True
        )
        outputs = self.session.run(
            None,
            {
                "input_ids": tokens["input_ids"],
                "attention_mask": tokens["attention_mask"],
                "token_type_ids": tokens["token_type_ids"],
            },
        )
        return outputs[0][0].mean(axis=0).tolist()
