---
name: image-describe
description: Describe the contents of an image file or URL in structured detail
---

# Image Describe Workflow

1. If the user provides a local path, upload to a short-lived public URL (or use `file://` if client supports).
2. Call `understand` tool with `media_urls=[url]` and `prompt="Describe this image in 3 paragraphs: visual composition, subjects, notable details."`
3. Use `provider="gemini"` and `tier="rich"` by default for best quality.
4. Return the text response with the model ID for attribution.
