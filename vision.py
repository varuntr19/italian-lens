import base64
import os

from anthropic import Anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = """You are the vision engine behind Italian Lens, a personal app that helps an \
English-speaking learner of Italian build a vocabulary database from things they photograph \
in daily life in Italy (menus, signs, supermarket shelves, receipts, notices, train stations, etc).

Given a photo, do three things:

1. Briefly describe the scene in English (one short sentence) so the user remembers the context \
later, e.g. "A trattoria menu board" or "Pasta shelf in a supermarket aisle".

2. Extract the Italian text that is actually useful to a learner (menu items, prices, product \
names, instructions, warnings, headlines). Skip boilerplate, logos, and irrelevant fine print. \
For each, give the Italian text, its English translation, and a category: one of \
"menu_item", "sign", "label", "instruction", "price", "other".

3. From that text, pick 3-10 individual words or short phrases genuinely worth adding to a \
vocabulary list (skip proper nouns and anything trivial). For each: the Italian word/phrase in \
its dictionary/base form, its English meaning, part of speech (e.g. noun, verb, adjective, \
phrase), and one short natural example sentence in Italian with its English translation.

If the photo contains no readable or useful Italian text, return an empty phrases and \
vocabulary list, and say so plainly in the scene description.

Call the record_findings tool with your findings. Respond only via that tool call."""

TOOL_SCHEMA = {
    "name": "record_findings",
    "description": "Record the scene description, extracted phrases, and vocabulary from a photo.",
    "input_schema": {
        "type": "object",
        "properties": {
            "scene_description": {"type": "string"},
            "phrases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "italian": {"type": "string"},
                        "english": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": ["menu_item", "sign", "label", "instruction", "price", "other"],
                        },
                    },
                    "required": ["italian", "english", "category"],
                },
            },
            "vocabulary": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "italian": {"type": "string"},
                        "english": {"type": "string"},
                        "part_of_speech": {"type": "string"},
                        "example_it": {"type": "string"},
                        "example_en": {"type": "string"},
                    },
                    "required": ["italian", "english", "part_of_speech", "example_it", "example_en"],
                },
            },
        },
        "required": ["scene_description", "phrases", "vocabulary"],
    },
}


class VisionError(RuntimeError):
    pass


def analyze_image(image_path, media_type="image/jpeg"):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise VisionError(
            "ANTHROPIC_API_KEY is not set. Add it to a .env file (see .env.example) and restart the server."
        )

    with open(image_path, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        tools=[TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "record_findings"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Analyze this photo for Italian Lens.",
                    },
                ],
            }
        ],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_findings":
            return block.input

    raise VisionError("Claude did not return a structured result.")
