from dataclasses import dataclass

from llm_studio.python_configs.text_causal_language_modeling_config import ConfigNLPCausalLMTokenizer, \
    ConfigNLPAugmentation, ConfigNLPCausalLMPrediction, ConfigNLPCausalLMEnvironment, ConfigNLPCausalLMLogging
from llm_studio.python_configs.text_dpo_language_modeling_config import (
    ConfigDPOCausalLMArchitecture,
    ConfigNLPDPOLMDataset,
    ConfigProblemBase, ConfigDPOCausalLMTraining,
)

"""
Configuration file for checking and debugging LLM Studio.
"""

DATA_DIRECTORY = "examples/data_oasst1"


@dataclass
class Config(ConfigProblemBase):
    output_directory: str = "examples/output_oasst1/"
    experiment_name: str = "example_oasst1"
    llm_backbone: str = "EleutherAI/pythia-1b"

    dataset: ConfigNLPDPOLMDataset = ConfigNLPDPOLMDataset(
        train_dataframe=f"{DATA_DIRECTORY}/train_full.csv",
        validation_strategy="automatic",
        validation_dataframe="",
        validation_size=0.01,
        prompt_column=("instruction",),
        answer_column="output",
        chosen_response_column="",
        rejected_response_column="",
        text_prompt_start="",
        text_answer_separator="",
        add_eos_token_to_prompt=True,
        add_eos_token_to_answer=True,
        mask_prompt_labels=True,
    )
    tokenizer: ConfigNLPCausalLMTokenizer = ConfigNLPCausalLMTokenizer(
        max_length_prompt=64,
        max_length_answer=64,
        max_length=128,
        padding_quantile=1.0,
        add_prompt_answer_tokens=False,
    )
    augmentation: ConfigNLPAugmentation = ConfigNLPAugmentation(
        token_mask_probability=0.0
    )
    architecture: ConfigDPOCausalLMArchitecture = ConfigDPOCausalLMArchitecture(
        backbone_dtype="float16",
    )
    training: ConfigDPOCausalLMTraining = ConfigDPOCausalLMTraining(
        optimizer="AdamW",
        learning_rate=0.00015,
        batch_size=4,
        epochs=1,
        lora=True,
        lora_r=1,
        lora_alpha=16,
        lora_dropout=0.05,
        lora_target_modules="",
        evaluate_before_training=True,
    )
    prediction: ConfigNLPCausalLMPrediction = ConfigNLPCausalLMPrediction(
        metric="BLEU",
        min_length_inference=2,
        max_length_inference=64,
        batch_size_inference=0,
        do_sample=False,
        num_beams=2,
        temperature=0.3,
        repetition_penalty=1.2,
        stop_tokens="",
    )
    environment: ConfigNLPCausalLMEnvironment = ConfigNLPCausalLMEnvironment(
        mixed_precision=True, number_of_workers=8, seed=1
    )
    logging: ConfigNLPCausalLMLogging = ConfigNLPCausalLMLogging()
