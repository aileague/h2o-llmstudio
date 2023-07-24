import os
from dataclasses import dataclass, field
from typing import Any

import llm_studio.src.datasets.text_dpo_language_modeling_ds
from llm_studio.python_configs.base import DefaultConfig
from llm_studio.python_configs.text_causal_language_modeling_config import (
    ConfigNLPAugmentation,
    ConfigNLPCausalLMArchitecture,
    ConfigNLPCausalLMDataset,
    ConfigNLPCausalLMEnvironment,
    ConfigNLPCausalLMLogging,
    ConfigNLPCausalLMPrediction,
    ConfigNLPCausalLMTokenizer,
    ConfigNLPCausalLMTraining,
)
from llm_studio.src import possible_values
from llm_studio.src.losses import text_dpo_language_modeling_losses
from llm_studio.src.models import text_dpo_language_modeling_model
from llm_studio.src.plots import text_dpo_language_modeling_plots
from llm_studio.src.utils.training_utils import generate_experiment_name


@dataclass
class ConfigNLPDPOLMDataset(ConfigNLPCausalLMDataset):
    dataset_class: Any = (
        llm_studio.src.datasets.text_dpo_language_modeling_ds.CustomDataset
    )
    # Always have full chat history. Chosen/Rejected prompt are only at the end of a conversation.
    limit_chained_samples: bool = True
    mask_prompt_labels: bool = False

    chosen_response_column: str = "chosen_response"
    rejected_response_column: str = "rejected_response"

    def __post_init__(self):
        super().__post_init__()
        self._visibility["limit_chained_samples"] = -1
        self._visibility["mask_prompt_labels"] = -1

        self._order.insert("chosen_response_column", after="answer_column")
        self._order.insert("rejected_response_column", after="chosen_response_column")


@dataclass
class ConfigDPOCausalLMTraining(ConfigNLPCausalLMTraining):
    loss_class: Any = text_dpo_language_modeling_losses.Losses
    loss_function: str = "DPOLoss"
    optimizer: str = "AdamW"


@dataclass
class ConfigDPOCausalLMArchitecture(ConfigNLPCausalLMArchitecture):
    model_class: Any = text_dpo_language_modeling_model.Model


@dataclass
class ConfigDPOPCausalLMLogging(ConfigNLPCausalLMLogging):
    plots_class: Any = text_dpo_language_modeling_plots.Plots


@dataclass
class ConfigProblemBase(DefaultConfig):
    output_directory: str = f"output/{os.path.basename(__file__).split('.')[0]}"
    experiment_name: str = field(default_factory=generate_experiment_name)
    _parent_experiment: str = ""
    llm_backbone: str = "EleutherAI/pythia-2.8b-deduped"

    dataset: ConfigNLPDPOLMDataset = field(default_factory=ConfigNLPDPOLMDataset)
    tokenizer: ConfigNLPCausalLMTokenizer = field(
        default_factory=ConfigNLPCausalLMTokenizer
    )
    architecture: ConfigDPOCausalLMArchitecture = field(
        default_factory=ConfigDPOCausalLMArchitecture
    )
    training: ConfigDPOCausalLMTraining = field(
        default_factory=ConfigDPOCausalLMTraining
    )
    augmentation: ConfigNLPAugmentation = field(default_factory=ConfigNLPAugmentation)
    prediction: ConfigNLPCausalLMPrediction = field(
        default_factory=ConfigNLPCausalLMPrediction
    )
    environment: ConfigNLPCausalLMEnvironment = field(
        default_factory=ConfigNLPCausalLMEnvironment
    )
    logging: ConfigDPOPCausalLMLogging = field(
        default_factory=ConfigDPOPCausalLMLogging
    )

    def __post_init__(self):
        super().__post_init__()

        self._visibility["output_directory"] = -1

        self._possible_values["llm_backbone"] = possible_values.String(
            values=(
                "h2oai/h2ogpt-gm-oasst1-en-2048-falcon-7b-v3",
                "h2oai/h2ogpt-gm-oasst1-en-2048-open-llama-7b",
                "h2oai/h2ogpt-gm-oasst1-en-2048-falcon-40b-v2",
                "tiiuae/falcon-7b",
                "tiiuae/falcon-40b",
                "openlm-research/open_llama_3b",
                "openlm-research/open_llama_7b",
                "openlm-research/open_llama_13b",
                "EleutherAI/gpt-j-6B",
                "EleutherAI/gpt-neox-20b",
                "facebook/opt-125m",
                "facebook/opt-2.7b",
                "EleutherAI/pythia-1b-deduped",
                "EleutherAI/pythia-2.8b-deduped",
                "EleutherAI/pythia-6.9b-deduped",
                "EleutherAI/pythia-12b-deduped",
                "togethercomputer/GPT-NeoXT-Chat-Base-20B",
            ),
            allow_custom=True,
        )

    @classmethod
    def from_dict(cls, cfg_dict):
        return cls(
            output_directory=cfg_dict.get(
                "output_directory", ConfigProblemBase.output_directory
            ),
            experiment_name=cfg_dict.get("experiment_name", generate_experiment_name()),
            llm_backbone=cfg_dict.get("llm_backbone", ConfigProblemBase.llm_backbone),
            dataset=ConfigNLPDPOLMDataset.from_dict(cfg_dict.get("dataset", {})),
            tokenizer=ConfigNLPCausalLMTokenizer.from_dict(
                cfg_dict.get("tokenizer", {})
            ),
            augmentation=ConfigNLPAugmentation.from_dict(
                cfg_dict.get("augmentation", {})
            ),
            architecture=ConfigDPOCausalLMArchitecture.from_dict(
                cfg_dict.get("architecture", {})
            ),
            training=ConfigDPOCausalLMTraining.from_dict(cfg_dict.get("training", {})),
            prediction=ConfigNLPCausalLMPrediction.from_dict(
                cfg_dict.get("prediction", {})
            ),
            environment=ConfigNLPCausalLMEnvironment.from_dict(
                cfg_dict.get("environment", {})
            ),
            logging=ConfigDPOPCausalLMLogging.from_dict(cfg_dict.get("logging", {})),
        )
