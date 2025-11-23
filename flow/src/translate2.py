"""
translate2.py - Translation script using translateindic library (HuggingFace-based)

This script translates Marathi text to English using the translateindic library,
similar to the approach in doc_translator_hf.py. It processes todo files and
generates translation cache files.

Usage:
    python translate2.py <todo_file> <translations_file>

    or for batch processing:
    python translate2.py <input_dir> <output_dir>

Example:
    python translate2.py subFlows/translate_/input/todos-1-100.json subFlows/translate_/output/trans-1-100.json
"""

import json
import sys
import traceback
from pathlib import Path


class Translator:
    """
    Translator class that uses the translateindic library for HuggingFace-based translation.
    This is similar to the approach used in doc_translator_hf.py.
    """

    def __init__(self, translations_file, todo_file, src_lang, tgt_lang, model_name="default", glossary_path=None):
        """
        Initialize the translator.

        Args:
            translations_file: Path to output translation cache file
            todo_file: Path to input todos JSON file
            src_lang: Source language code (e.g., "mar_Deva" for Marathi)
            tgt_lang: Target language code (e.g., "eng_Latn" for English)
            model_name: Model name (default: "default" uses ai4bharat/indictrans2-en-indic-1B)
            glossary_path: Optional path to glossary YAML file
        """
        print(f"[Translator] Initializing translator")
        print(f"[Translator] Source language: {src_lang}, Target language: {tgt_lang}")
        print(f"[Translator] Model: {model_name}")

        self.translations_file = Path(translations_file)
        self.todo_file = Path(todo_file)
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang

        # Load todos
        print(f"[Translator] Loading todos from: {self.todo_file}")
        try:
            if self.todo_file.exists() and self.todo_file.stat().st_size > 0:
                todo_dict = json.loads(self.todo_file.read_text())
                self.para_todos = todo_dict.get("paras", [])
                self.sent_todos = todo_dict.get("sents", [])
                print(f"[Translator] Loaded {len(self.para_todos)} paragraph todos and {len(self.sent_todos)} sentence todos")
            else:
                print(f"[Translator] WARNING: No todos file found or file is empty at {self.todo_file}")
                self.para_todos = []
                self.sent_todos = []
        except json.JSONDecodeError as e:
            print(f"[Translator] ERROR: Invalid JSON in todos file: {e}")
            print(f"[Translator] File: {self.todo_file}")
            raise
        except Exception as e:
            print(f"[Translator] ERROR: Failed to load todos file: {e}")
            print(f"[Translator] File: {self.todo_file}")
            raise

        # Load existing translations
        self.translations = self.load_translations()

        # Initialize the translateindic Translator (lazy loading)
        self.translator = None
        self.model_name = model_name
        self.glossary_path = Path(glossary_path) if glossary_path else None

    def load_translator(self):
        """
        Load the translateindic Translator model.
        Uses the same approach as doc_translator_hf.py.
        """
        if self.translator is not None:
            return self.translator

        print(f"[Translator] Loading translateindic.Translator model...")

        try:
            from translateindic import Translator as TranslateIndicTranslator

            if self.glossary_path and self.glossary_path.exists():
                print(f"[Translator] Using glossary from: {self.glossary_path}")
                self.translator = TranslateIndicTranslator(
                    self.model_name,
                    self.src_lang,
                    self.tgt_lang,
                    glossary_path=self.glossary_path,
                    enable_numeric=True,
                )
            else:
                if self.glossary_path:
                    print(f"[Translator] Glossary path specified but not found: {self.glossary_path}")
                print(f"[Translator] Initializing translator without glossary")
                self.translator = TranslateIndicTranslator(
                    self.model_name,
                    self.src_lang,
                    self.tgt_lang,
                    enable_numeric=True
                )

            print(f"[Translator] Model loaded successfully")
            return self.translator

        except ImportError as e:
            print(f"[Translator] ERROR: Could not import translateindic library")
            print(f"[Translator] Please install it with: pip install git+https://github.com/orgpedia/translateIndic.git")
            raise e

    def load_translations(self):
        """
        Load existing translations from cache file.

        Returns:
            dict: Dictionary mapping source text to translated text
        """
        translations = {}

        try:
            if self.translations_file.exists() and self.translations_file.stat().st_size > 0:
                print(f"[Translator] Loading existing translations from: {self.translations_file}")
                json_list = json.loads(self.translations_file.read_text())
                for trans_dict in json_list:
                    m, e = trans_dict["mr"], trans_dict["en"]
                    translations[m] = e
                print(f"[Translator] Loaded {len(translations)} existing translations")
            else:
                print(f"[Translator] No existing translations file found")
        except json.JSONDecodeError as e:
            print(f"[Translator] ERROR: Invalid JSON in translations file: {e}")
            print(f"[Translator] File: {self.translations_file}")
            print(f"[Translator] Starting with empty translations cache")
        except KeyError as e:
            print(f"[Translator] ERROR: Missing required key in translations file: {e}")
            print(f"[Translator] File: {self.translations_file}")
            print(f"[Translator] Starting with empty translations cache")
        except Exception as e:
            print(f"[Translator] ERROR: Failed to load translations file: {e}")
            print(f"[Translator] File: {self.translations_file}")
            print(f"[Translator] Starting with empty translations cache")

        return translations

    def save_translations(self):
        """
        Save translations to cache file in sorted order.
        """
        try:
            save_trans = sorted(
                [{"mr": k, "en": v} for (k, v) in self.translations.items()],
                key=lambda d: d["mr"],
            )
            print(f"[Translator] Saving {len(save_trans)} translations to {self.translations_file}")

            # Ensure parent directory exists
            self.translations_file.parent.mkdir(parents=True, exist_ok=True)

            self.translations_file.write_text(
                json.dumps(save_trans, indent=2, ensure_ascii=False)
            )
            print(f"[Translator] Translations saved successfully")
        except Exception as e:
            print(f"[Translator] ERROR: Failed to save translations: {e}")
            print(f"[Translator] File: {self.translations_file}")
            print(f"[Translator] Stack trace:")
            traceback.print_exc()
            raise

    def translate_paragraphs(self, para_texts):
        """
        Translate paragraphs using the translateindic library.

        Args:
            para_texts: List of paragraph texts to translate

        Returns:
            List of translated paragraphs
        """
        if not para_texts:
            return []

        print(f"[Translator] Translating {len(para_texts)} paragraphs...")
        translator = self.load_translator()

        try:
            # Use the translate_paragraphs method from translateindic.Translator
            para_trans = translator.translate_paragraphs(para_texts)
            print(f"[Translator] Paragraph translation completed")
            return para_trans
        except Exception as e:
            print(f"[Translator] ERROR during paragraph translation: {e}")
            print(f"[Translator] Error type: {type(e).__name__}")
            print(f"[Translator] Stack trace:")
            traceback.print_exc()
            print(f"[Translator] Attempting fallback: translating as sentences...")

            # Fallback: try translating as sentences instead
            try:
                para_trans = translator.translate_sentences(para_texts)
                print(f"[Translator] Fallback translation completed")
                return para_trans
            except Exception as e2:
                print(f"[Translator] ERROR during fallback translation: {e2}")
                print(f"[Translator] Error type: {type(e2).__name__}")
                print(f"[Translator] Stack trace:")
                traceback.print_exc()
                print(f"[Translator] Skipping these {len(para_texts)} paragraphs")
                return ["[TRANSLATION_FAILED]"] * len(para_texts)

    def translate_sentences(self, sent_texts):
        """
        Translate sentences using the translateindic library.

        Args:
            sent_texts: List of sentence texts to translate

        Returns:
            List of translated sentences
        """
        if not sent_texts:
            return []

        print(f"[Translator] Translating {len(sent_texts)} sentences...")
        translator = self.load_translator()

        try:
            # Use the translate_sentences method from translateindic.Translator
            sent_trans = translator.translate_sentences(sent_texts)
            print(f"[Translator] Sentence translation completed")
            return sent_trans
        except Exception as e:
            print(f"[Translator] ERROR during sentence translation: {e}")
            print(f"[Translator] Error type: {type(e).__name__}")
            print(f"[Translator] Stack trace:")
            traceback.print_exc()

            # Try processing in smaller batches
            print(f"[Translator] Attempting to process in smaller batches...")
            batch_size = 2
            sent_trans = []

            for i in range(0, len(sent_texts), batch_size):
                batch = sent_texts[i:i+batch_size]
                print(f"[Translator] Processing batch {i//batch_size + 1}/{(len(sent_texts)-1)//batch_size + 1} ({len(batch)} sentences)")
                try:
                    batch_trans = translator.translate_sentences(batch)
                    sent_trans.extend(batch_trans)
                    print(f"[Translator] Batch {i//batch_size + 1} completed successfully")
                except Exception as e_batch:
                    print(f"[Translator] ERROR in batch {i//batch_size + 1}: {e_batch}")
                    print(f"[Translator] Error type: {type(e_batch).__name__}")
                    print(f"[Translator] Stack trace:")
                    traceback.print_exc()
                    print(f"[Translator] Marking {len(batch)} sentences as failed")
                    sent_trans.extend(["[TRANSLATION_FAILED]"] * len(batch))

            return sent_trans

    def translate(self):
        """
        Main translation method. Processes todos and generates translations.
        """
        if not self.para_todos and not self.sent_todos:
            print("[Translator] No todos to translate")
            return

        # Filter out already translated texts
        para_texts = [p for p in self.para_todos if p not in self.translations]
        sent_texts = [s for s in self.sent_todos if s not in self.translations]

        print(f"[Translator] Need to translate: {len(para_texts)} paragraphs, {len(sent_texts)} sentences")
        print(f"[Translator] Already cached: {len(self.para_todos) - len(para_texts)} paragraphs, {len(self.sent_todos) - len(sent_texts)} sentences")

        if not para_texts and not sent_texts:
            print("[Translator] All texts already translated!")
            return

        # Translate paragraphs
        if para_texts:
            print("\n[Translator] ******** TRANSLATING PARAGRAPHS ***********")
            para_trans = self.translate_paragraphs(para_texts)

            # Add to cache
            for (p, t) in zip(para_texts, para_trans):
                self.translations[p] = t

            # Save incrementally
            self.save_translations()
            print(f"[Translator] Added {len(para_texts)} paragraph translations to cache")

        # Translate sentences
        if sent_texts:
            print("\n[Translator] ******** TRANSLATING SENTENCES ***********")
            sent_trans = self.translate_sentences(sent_texts)

            # Add to cache
            for (s, t) in zip(sent_texts, sent_trans):
                self.translations[s] = t

            # Save incrementally
            self.save_translations()
            print(f"[Translator] Added {len(sent_texts)} sentence translations to cache")

        print("\n[Translator] ******** TRANSLATION COMPLETE ***********")
        print(f"[Translator] Total translations in cache: {len(self.translations)}")


def process_single_file(todo_file, trans_file, src_lang="mar_Deva", tgt_lang="eng_Latn", model_name="default", glossary_path=None):
    """
    Process a single todo file and generate translations.

    Args:
        todo_file: Path to todos JSON file
        trans_file: Path to output translations JSON file
        src_lang: Source language code
        tgt_lang: Target language code
        model_name: Model name to use
        glossary_path: Optional glossary path
    """
    print(f"\n{'='*80}")
    print(f"Processing: {todo_file}")
    print(f"Output to: {trans_file}")
    print(f"{'='*80}\n")

    try:
        translator = Translator(
            trans_file,
            todo_file,
            src_lang,
            tgt_lang,
            model_name=model_name,
            glossary_path=glossary_path
        )
        translator.translate()
        print(f"\n[SUCCESS] File processing completed: {todo_file}")
    except Exception as e:
        print(f"\n[FATAL ERROR] Failed to process file: {todo_file}")
        print(f"[FATAL ERROR] Error: {e}")
        print(f"[FATAL ERROR] Error type: {type(e).__name__}")
        print(f"[FATAL ERROR] Stack trace:")
        traceback.print_exc()
        raise


def process_directory(input_dir, output_dir, src_lang="mar_Deva", tgt_lang="eng_Latn", model_name="default", glossary_path=None):
    """
    Process all todo files in a directory.

    Args:
        input_dir: Directory containing todos-*.json files
        output_dir: Directory for output trans-*.json files
        src_lang: Source language code
        tgt_lang: Target language code
        model_name: Model name to use
        glossary_path: Optional glossary path
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # Validate input directory
    if not input_path.exists():
        print(f"[FATAL ERROR] Input directory does not exist: {input_dir}")
        sys.exit(1)

    if not input_path.is_dir():
        print(f"[FATAL ERROR] Input path is not a directory: {input_dir}")
        sys.exit(1)

    # Find all todos files
    todo_files = list(input_path.glob('todos-*.json'))

    if not todo_files:
        print(f"[ERROR] No todos-*.json files found in {input_dir}")
        return

    print(f"\n[Translator] Found {len(todo_files)} todo files to process")

    failed_files = []
    successful_files = []

    for idx, todo_file in enumerate(todo_files, 1):
        print(f"\n[Translator] Processing file {idx}/{len(todo_files)}")

        # Generate output filename
        trans_file = output_path / todo_file.name.replace('todos', 'trans')

        try:
            process_single_file(
                todo_file,
                trans_file,
                src_lang=src_lang,
                tgt_lang=tgt_lang,
                model_name=model_name,
                glossary_path=glossary_path
            )
            successful_files.append(todo_file)
        except Exception as e:
            print(f"[ERROR] Skipping file {todo_file} due to error")
            failed_files.append((todo_file, str(e)))

    # Print summary
    print(f"\n{'='*80}")
    print(f"BATCH PROCESSING SUMMARY")
    print(f"{'='*80}")
    print(f"Total files: {len(todo_files)}")
    print(f"Successful: {len(successful_files)}")
    print(f"Failed: {len(failed_files)}")

    if failed_files:
        print(f"\nFailed files:")
        for file, error in failed_files:
            print(f"  - {file}: {error}")
    print(f"{'='*80}\n")


def main():
    """
    Main entry point for the script.

    Supports two modes:
    1. Single file: python translate2.py <todo_file> <trans_file>
    2. Directory batch: python translate2.py <input_dir> <output_dir>
    """
    print(f"[Translator] Starting translate2.py")
    print(f"[Translator] Command: {' '.join(sys.argv)}")

    if len(sys.argv) < 3:
        print("[ERROR] Insufficient arguments")
        print("Usage:")
        print(f"  {sys.argv[0]} <todo_file> <translations_file>")
        print(f"  {sys.argv[0]} <input_dir> <output_dir>")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} todos-1-100.json trans-1-100.json")
        print(f"  {sys.argv[0]} input/ output/")
        sys.exit(1)

    try:
        path1 = Path(sys.argv[1])
        path2 = Path(sys.argv[2])

        # Validate first path exists
        if not path1.exists():
            print(f"[FATAL ERROR] Input path does not exist: {path1}")
            sys.exit(1)

        # Optional arguments
        src_lang = sys.argv[3] if len(sys.argv) > 3 else "mar_Deva"
        tgt_lang = sys.argv[4] if len(sys.argv) > 4 else "eng_Latn"
        model_name = sys.argv[5] if len(sys.argv) > 5 else "default"
        glossary_path = sys.argv[6] if len(sys.argv) > 6 else None

        # Determine mode based on whether first argument is a directory
        if path1.is_dir():
            print("[Translator] Running in DIRECTORY mode")
            process_directory(path1, path2, src_lang, tgt_lang, model_name, glossary_path)
        else:
            print("[Translator] Running in SINGLE FILE mode")
            process_single_file(path1, path2, src_lang, tgt_lang, model_name, glossary_path)

        print("\n[Translator] *** SCRIPT COMPLETED SUCCESSFULLY ***\n")

    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Script interrupted by user (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL ERROR] Unhandled exception in main: {e}")
        print(f"[FATAL ERROR] Error type: {type(e).__name__}")
        print(f"[FATAL ERROR] Stack trace:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
