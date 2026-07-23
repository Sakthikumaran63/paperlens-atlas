export type PaperStatus = "ready" | "processing" | "failed";

export interface Paper {
  id: string;
  title: string;
  authors: string[];
  year: number;
  venue: string;
  addedAt: string;
  pages: number;
  status: PaperStatus;
  abstract: string;
  tags: string[];
  keyContributions: string[];
  methodology: string[];
  results: string[];
  citations: number;
}

export const mockPapers: Paper[] = [
  {
    id: "attention-is-all-you-need",
    title: "Attention Is All You Need",
    authors: ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones"],
    year: 2017,
    venue: "NeurIPS",
    addedAt: "2026-07-14",
    pages: 15,
    status: "ready",
    citations: 132480,
    tags: ["Transformers", "NLP", "Attention"],
    abstract:
      "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks. We propose a new simple architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
    keyContributions: [
      "Introduces the Transformer, an architecture built entirely on self-attention.",
      "Removes the need for recurrence and convolutions in sequence modeling.",
      "Achieves state-of-the-art BLEU scores on WMT 2014 English-to-German and English-to-French translation.",
    ],
    methodology: [
      "Encoder-decoder stack with multi-head scaled dot-product attention.",
      "Positional encodings injected via sinusoidal functions.",
      "Trained with Adam, warmup schedule, label smoothing, and dropout.",
    ],
    results: [
      "28.4 BLEU on WMT 2014 EN-DE, a 2.0 BLEU improvement over prior best.",
      "41.8 BLEU on WMT 2014 EN-FR after 3.5 days on eight P100 GPUs.",
    ],
  },
  {
    id: "bert",
    title:
      "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
    authors: ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
    year: 2019,
    venue: "NAACL",
    addedAt: "2026-07-18",
    pages: 16,
    status: "ready",
    citations: 98210,
    tags: ["Pre-training", "NLP", "Language Models"],
    abstract:
      "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. BERT is designed to pre-train deep bidirectional representations from unlabeled text.",
    keyContributions: [
      "Masked language modeling objective enabling deep bidirectional pre-training.",
      "Next-sentence prediction task capturing inter-sentence relationships.",
      "Single fine-tuned model achieves state-of-the-art on 11 NLP tasks.",
    ],
    methodology: [
      "Pre-training on BooksCorpus (800M words) and English Wikipedia (2.5B words).",
      "Two model sizes: BERT-Base (110M params) and BERT-Large (340M params).",
      "Fine-tuning on downstream tasks with a lightweight task-specific head.",
    ],
    results: [
      "GLUE benchmark: 80.5% (7.7% absolute improvement).",
      "SQuAD v1.1 F1: 93.2 (1.5% improvement).",
      "MultiNLI accuracy: 86.7% (4.6% improvement).",
    ],
  },
  {
    id: "resnet",
    title: "Deep Residual Learning for Image Recognition",
    authors: ["Kaiming He", "Xiangyu Zhang", "Shaoqing Ren", "Jian Sun"],
    year: 2016,
    venue: "CVPR",
    addedAt: "2026-07-20",
    pages: 12,
    status: "ready",
    citations: 214300,
    tags: ["Computer Vision", "CNN", "Residual Networks"],
    abstract:
      "Deeper neural networks are more difficult to train. We present a residual learning framework to ease the training of networks that are substantially deeper than those used previously.",
    keyContributions: [
      "Introduces residual connections that let layers learn identity mappings.",
      "Enables training of networks with 152+ layers without degradation.",
      "Won 1st place on ILSVRC 2015 classification, detection, and localization.",
    ],
    methodology: [
      "Building block: two 3x3 convolutions with an identity shortcut connection.",
      "Bottleneck variant for deeper networks using 1x1-3x3-1x1 convolutions.",
      "Trained with SGD, batch normalization, and standard ImageNet augmentation.",
    ],
    results: [
      "ImageNet top-5 error: 3.57% (ensemble).",
      "COCO detection improved by 28% relative to the previous best.",
    ],
  },
  {
    id: "clip",
    title: "Learning Transferable Visual Models From Natural Language Supervision",
    authors: ["Alec Radford", "Jong Wook Kim", "Chris Hallacy", "et al."],
    year: 2021,
    venue: "ICML",
    addedAt: "2026-07-22",
    pages: 48,
    status: "processing",
    citations: 18420,
    tags: ["Multimodal", "Vision-Language", "Contrastive"],
    abstract:
      "We demonstrate that contrastive pre-training on 400M image–text pairs learns transferable visual representations without task-specific supervision.",
    keyContributions: [
      "Introduces CLIP, contrastive image-text pre-training at scale.",
      "Enables zero-shot transfer across a wide range of vision benchmarks.",
    ],
    methodology: [
      "Joint image-text embedding trained with contrastive loss.",
      "Large-scale dataset of 400M image-caption pairs from the web.",
    ],
    results: ["Zero-shot ImageNet accuracy comparable to fully supervised ResNet-50."],
  },
];

export const recentActivity = [
  { id: "a1", kind: "upload", title: "Uploaded 'Attention Is All You Need'", when: "2h ago" },
  { id: "a2", kind: "question", title: "Asked: What is the attention mechanism?", when: "3h ago" },
  { id: "a3", kind: "summary", title: "Generated summary for 'BERT'", when: "yesterday" },
  { id: "a4", kind: "upload", title: "Uploaded 'Deep Residual Learning'", when: "2d ago" },
  { id: "a5", kind: "question", title: "Asked: How does BERT differ from GPT?", when: "3d ago" },
];

export function getPaper(id: string): Paper | undefined {
  return mockPapers.find((p) => p.id === id);
}
