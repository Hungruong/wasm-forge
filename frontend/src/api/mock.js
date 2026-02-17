export const mockModels = [
  {
    name: "llama3",
    type: "text",
    description:
      "General-purpose text model for summarization, translation, and analysis",
  },
  {
    name: "llava",
    type: "vision",
    description:
      "Multimodal model for image understanding and visual reasoning",
  },
  {
    name: "mistral",
    type: "code",
    description:
      "Specialized model for code review, generation, and debugging",
  },
];

export const mockPlugins = [
  {
    name: "summarize",
    description: "Condense long text into key points",
    input_type: "text",
    input_hint: "Paste any article or long text you want summarized",
    calls: 1,
  },
  {
    name: "translate",
    description: "Translate text to Vietnamese",
    input_type: "text",
    input_hint: "Paste English text to translate",
    calls: 1,
  },
  {
    name: "moderator",
    description: "Content safety analysis with scoring and report",
    input_type: "text",
    input_hint: "Paste text to check for harmful content",
    calls: 3,
  },
  {
    name: "code_review",
    description: "Find bugs, security issues, and optimizations",
    input_type: "text",
    input_hint: "Paste code to review (Python, JavaScript, etc.)",
    calls: 3,
  },
  {
    name: "image_describe",
    description: "Describe the content of an uploaded image",
    input_type: "file",
    input_hint: "Upload an image (JPG, PNG)",
    calls: 1,
  },
  {
    name: "batch_analyze",
    description: "Analyze structured data with multiple fields",
    input_type: "json",
    input_hint: '{"text": "your text", "task": "summarize|translate|analyze"}',
    calls: 2,
  },
];

export const mockRunResult = {
  status: "success",
  result:
    "The article discusses the rapid evolution of distributed computing paradigms, highlighting the shift from monolithic architectures to microservices and serverless patterns. Key findings suggest a 40% improvement in deployment velocity when adopting container-based workflows.",
};