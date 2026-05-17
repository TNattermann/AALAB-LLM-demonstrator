from ast import literal_eval
from itertools import cycle
from src.explorer import Explorer
from src.utils import entropy_to_color, probability_to_color
from src.Layout.layouter import Layouter
from src.completion import StoryCompletion
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textwrap import dedent
import sys
import os
import argparse
import tomli 
from datetime import datetime
from textual.app import App, ComposeResult
import asyncio
from textual.containers import Horizontal, Vertical
from textual.widgets import LoadingIndicator, Footer, Header, Static, DataTable, Label


class TokenExplorer(App):
    """Main application class."""

    stop_text_animation: bool = False
    index: str = ""
    CSS = """
    .hidden {
        display: none;
    }

    #spinner {
        dock: top;
        align: center middle;
        height: 5;
    }
    
    #overlay_container {
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.4);  /* semi-transparent overlay */
    content-align: center middle;
    layer: overlay;               /* float above all other widgets */
}
    """

    display_modes = cycle(["prompt", "prob", "entropy"])
    display_mode = reactive(next(display_modes))

    BINDINGS = [("e", "change_display_mode", "Mode"),
                ("left,h", "pop_token", "Back"),
                ("right,l", "append_token", "Add"),
                ("d", "add_prompt", "New"),
                ("a", "remove_prompt", "Del"),
                ("w", "increment_prompt", "Next"),
                ("s", "decrement_prompt", "Prev"),
                ("x", "save_prompt", "Save"),
                ("j", "select_next", "Down"),
                ("k", "select_prev", "Up"),
                ("r", "toggle_struct", "Toggle struct"),
                ("R", "next_struct", "Next struct")
                ]
    
    
    def __init__(self, mode, precompile=False):
        super().__init__()
        # Add support for multiple prompts.
        self.mode = mode
        self.config = self.load_config()
        self.model_name = self.config["model"]["name"]
        self.hidden_prompt = self.config["prompt"]["hidden_prompt"]
        self.prompt = self.config["prompt"]["german_prompt"]
        self.prompt_en = self.config["prompt"]["english_prompt"]
        self.tokens_to_show = self.config["display"]["tokens_to_show"]
        self.max_prompts = self.config["prompt"]["max_prompts"]
        self.testing = self.config["debugging"]["testing"]

        self.prompts = [self.prompt, self.prompt_en, self.prompt]
        self.prompt_index = 2
        self.index = ""
        self.explorer = Explorer(self.config, self.model_name)
        self.explorer.set_prompt(self.hidden_prompt+self.prompt)
        self.rows = self._top_tokens_to_rows(
            self.explorer.get_top_n_tokens(n=self.tokens_to_show)
            )
        self.selected_row = 0  # Track currently selected token row
        self.regex_structs = self._get_regex_structs()
        # this is the position of the stuct in the prompt
        self.struct_index = None
        # this is the position of the struct in the regex_structs list
        self.current_struct_index = 0
        if precompile:
            self.precompile_regex_structs()

    def load_config(self):
        try:
            with open(f"config_{self.mode}.toml", "rb") as f:
                return tomli.load(f)
        except FileNotFoundError:
            print("Config file not found, using default values")
            return {
                "model": "Qwen/Qwen2.5-0.5B",
                "example_prompt": "Once upon a time, there was a",
                "tokens_to_show": 30,
                "max_prompts": 9
            }

    def precompile_regex_structs(self):
        print("Precompiling regex structs, this may take a while...")
        for name, regex in self.regex_structs:
            print(name)
            self.explorer.set_guide(regex)
            self.explorer.clear_guide()
        self.explorer.clear_guide()

    def _get_regex_structs(self):
        try:
            struct_files = []
            # Get all files in struct directory
            for file in os.listdir("struct"):
                if file.endswith(".txt"):
                    file_path = os.path.join("struct", file)
                    try:
                        with open(file_path, "r") as f:
                            # Get first line and strip whitespace
                            regex = f.readline().strip()
                            # Remove file extension and add tuple
                            name = os.path.splitext(file)[0]
                            struct_files.append((name, str(literal_eval(regex))))
                    except:
                        # Skip files that can't be read
                        continue
            return struct_files
        except FileNotFoundError:
            return []

    def _top_tokens_to_rows(self, tokens):
        return [("token_id", "token", "prob")] + [
            (token["token_id"], token["token"], "%3d%%" % (token["probability"] * 100))
            for token in tokens
        ]
        
    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static(id="results")
            yield DataTable(id="table")
        yield Footer()
        yield LoadingIndicator(id="spinner", classes="hidden")

    def _refresh_table(self):
        table = self.query_one(DataTable)
        self.rows = self._top_tokens_to_rows(
            self.explorer.get_top_n_tokens(n=self.tokens_to_show)
            )
        table.clear()
        table.add_rows(self.rows[1:])
        # Reset cursor to top
        self.selected_row = 0
        table.move_cursor(row=self.selected_row)
        self.query_one("#results", Static).update(self._render_prompt())
    

    def _render_structure_section(self):
        struct_section = ""
        if self.explorer.guide_is_finished():
            struct_section = f"[on red]{self.regex_structs[self.current_struct_index][0]}[/on]"
        elif self.struct_index is not None:
            struct_section = f"[on green]{self.regex_structs[self.current_struct_index][0]}[/on]"

        else:
            struct_section = f"[on grey]{self.regex_structs[self.current_struct_index][0]}[/on]"
        return struct_section
    
    def _render_prompt(self):
        if self.display_mode == "entropy":
            entropy_legend = "".join([
                f"[on {entropy_to_color(i/10)}] {i/10:.2f} [/on]"
                for i in range(11)
                ])
            prompt_legend = f"[bold]Token entropy:[/bold]{entropy_legend}"
            token_entropies = self.explorer.get_prompt_token_normalized_entropies()
            token_strings = self.explorer.get_prompt_tokens_strings()
            prompt_text = "".join(f"[on {entropy_to_color(entropy)}]{token}[/on]" for token, entropy in zip(token_strings, token_entropies))
        elif self.display_mode == "prob":
            prob_legend = "".join([
                f"[on {probability_to_color(i/10)}] {i/10:.2f} [/on]"
                for i in range(11)
                ])
            prompt_legend = f"[bold]Token prob:[/bold]{prob_legend}"
            token_probs = self.explorer.get_prompt_token_probabilities()
            token_strings = self.explorer.get_prompt_tokens_strings()
            prompt_text = "".join(f"[on {probability_to_color(prob)}]{token}[/on]" for token, prob in zip(token_strings, token_probs))
        else:
            prompt_text = self.explorer.get_prompt()[len(self.hidden_prompt):] # slice hidden prompt
            prompt_legend = ""
        return dedent(f"""
{prompt_text}





{prompt_legend}
[bold]Prompt[/bold] {self.prompt_index+1}/{len(self.prompts)} tokens: {len(self.explorer.prompt_tokens)}
[bold]Struct[/bold] {self._render_structure_section()}
""")
    
    async def on_mount(self) -> None:
        self.query_one("#results", Static).update(self._render_prompt())
        table = self.query_one(DataTable)
        table.add_columns(*self.rows[0])
        table.add_rows(self.rows[1:])
        table.cursor_type = "row"

    def action_next_struct(self):
        self.current_struct_index = (self.current_struct_index + 1) % len(self.regex_structs)
        self.query_one("#results", Static).update(self._render_prompt())

    def action_toggle_struct(self):
        if self.struct_index is None:
            # this is the theoretical index of the first
            # structure token when structured gen is activated
            # even though that token *doesn't* exist yet.
            # this track to help with backtracking.
            self.struct_index = len(self.explorer.get_prompt_tokens())
            self.explorer.set_guide(self.regex_structs[self.current_struct_index][1])
        else:
            self.struct_index = None
            self.explorer.clear_guide()
        self.query_one("#results", Static).update(self._render_prompt())
        self._refresh_table()
        
    def action_add_prompt(self):
        if len(self.prompts) < self.max_prompts:
            self.prompts.append(self.explorer.get_prompt())
            self.prompt_index = len(self.prompts) -1
            self.explorer.set_prompt(self.prompts[self.prompt_index])
            self.query_one("#results", Static).update(self._render_prompt())
            self._refresh_table()

    def action_remove_prompt(self):
        if len(self.prompts) > 1:
            self.prompts.pop(self.prompt_index)
            self.prompt_index = (self.prompt_index - 1) % len(self.prompts)
            self.explorer.set_prompt(self.prompts[self.prompt_index])
            self.query_one("#results", Static).update(self._render_prompt())
            self._refresh_table()
    
    def action_increment_prompt(self):
        self.prompt_index = (self.prompt_index + 1) % len(self.prompts)
        self.explorer.set_prompt(self.prompts[self.prompt_index])
        self.query_one("#results", Static).update(self._render_prompt())
        self._refresh_table()

    def action_decrement_prompt(self):
        self.prompt_index = (self.prompt_index - 1) % len(self.prompts)
        self.explorer.set_prompt(self.prompts[self.prompt_index])
        self.query_one("#results", Static).update(self._render_prompt())
        self._refresh_table()

    def action_change_display_mode(self):
        self.display_mode = next(self.display_modes)
        self.query_one("#results", Static).update(self._render_prompt())

    async def action_save_prompt(self):
        prompt_text = self.explorer.get_prompt()
        self.index = f"{self.prompt_index}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

        # =========================================================
        # Overlay Setup
        # =========================================================

        # --- Spinner ---
        spinner = LoadingIndicator(id="spinner")
        spinner.styles.margin = (1, 0, 2, 0)

        # --- Initial loading label ---
        spinner_label = Label(
            "Completing your story...",
            id="spinner_label"
        )

        spinner_label.styles.color = "white"
        spinner_label.styles.bold = True
        spinner_label.styles.width = "100%"
        spinner_label.styles.content_align = ("center", "middle")
        spinner_label.styles.padding = (1, 2)

        # --- Crawling text label ---
        anim_label = Label("", id="animation_label")

        anim_label.styles.color = "white"
        anim_label.styles.bold = True

        # Bigger text canvas
        anim_label.styles.width = "90%"
        anim_label.styles.height = "auto"
        anim_label.styles.min_height = 20

        # Wrapping
        anim_label.styles.text_wrap = "wrap"

        # Internal spacing
        anim_label.styles.padding = (2, 4)

        # Visual styling
        anim_label.styles.background = "#1e1e1e"
        anim_label.styles.border = ("round", "white")

        # Hide initially
        anim_label.styles.display = "none"

        # --- Overlay container ---
        overlay = Vertical(
            spinner,
            spinner_label,
            anim_label,
            id="overlay_container"
        )

        overlay.styles.width = "100%"
        overlay.styles.height = "100%"

        overlay.styles.align = ("center", "middle")

        overlay.styles.padding = (3, 6)

        overlay.styles.layer = "overlay"

        overlay.styles.background = "rgba(0,0,0,0.75)"

        # Mount overlay
        await self.mount(overlay)

        # =========================================================
        # Phase 1: Initial blocking work
        # =========================================================

        await asyncio.to_thread(
            self._save_prompt_work_partial,
            prompt_text
        )

        # =========================================================
        # Phase 2: Generate story text
        # =========================================================

        ft = StoryCompletion(prompt_text, self.config)

        generated_text_file = (
            f"data/{self.index}_story.txt"
        )

        await asyncio.to_thread(
            ft.generate_text,
            "data/",
            self.index
        )

        # =========================================================
        # Transition to crawling animation
        # =========================================================

        spinner.styles.display = "none"
        spinner_label.styles.display = "none"

        anim_label.styles.display = "block"

        # =========================================================
        # Crawling text animation
        # =========================================================

        self.stop_text_animation = False

        async def animate_label():

            with open(
                    generated_text_file,
                    "r",
                    encoding="utf-8"
            ) as f:

                text = f.read()

            words = text.split()

            current_text = ""

            for word in words:

                if self.stop_text_animation:
                    break

                current_text += word + " "

                anim_label.update(current_text)

                await asyncio.sleep(0.15)

        animation_task = asyncio.create_task(
            animate_label()
        )

        # =========================================================
        # Remaining heavy work
        # =========================================================

        background_task = asyncio.create_task(
            asyncio.to_thread(
                self._save_prompt_work_final,
                prompt_text
            )
        )

        # Wait until one finishes first
        done, pending = await asyncio.wait(
            [animation_task, background_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Stop animation if backend finishes first
        self.stop_text_animation = True

        # Finish remaining tasks cleanly
        await asyncio.gather(
            *pending,
            return_exceptions=True
        )

        # =========================================================
        # Cleanup
        # =========================================================

        await overlay.remove()

    def _save_prompt_work_partial(self, prompt_text):
        """Blocking work before text generation"""
        # Save the prompt to file
        with open(f"data/prompts/prompt_{self.index}.txt", "w") as f:
            f.write(prompt_text)

    def _save_prompt_work_final(self, prompt_text):
        """Blocking work after text generation"""
        ft = StoryCompletion(prompt_text, self.config)
        ft.generate_image("data/", self.index)

        layouter = Layouter(self.index, self.mode, path_to_tex="src/Layout", path_to_data=".")
        layouter.formatter()
        if not self.testing:
            layouter.printer(copies=self.config["printer"]["num_prints"])

    def action_select_next(self):
        """Move selection down one row"""
        if self.selected_row < len(self.rows) - 2:  # -2 for header row
            self.selected_row += 1
            table = self.query_one(DataTable)
            table.move_cursor(row=self.selected_row)
            
    def action_select_prev(self):
        """Move selection up one row"""
        if self.selected_row > 0:
            self.selected_row -= 1
            table = self.query_one(DataTable)
            table.move_cursor(row=self.selected_row)

    def action_append_token(self):
        """Append currently selected token"""
        # TODO: here we need to distinguish between a dead and finished guide

        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            if len(self.rows) > (table.cursor_row+1):
                self.explorer.append_token(self.rows[table.cursor_row+1][0])
                if self.explorer.guide_is_dead():
                    self.explorer.clear_guide()
                    self.struct_index = None
                self.prompts[self.prompt_index] = self.explorer.get_prompt()
                self._refresh_table()  # This will reset cursor position

    def action_pop_token(self):
        if len(self.explorer.get_prompt_tokens()) > 1:
            self.explorer.pop_token()
            if self.explorer.guide is not None:
                self.explorer.clear_guide()
                #  need to add logic for backtracking the guide
                self.explorer.set_guide(self.regex_structs[self.current_struct_index][1]
                                        ,ff_from=self.struct_index)
            self.prompts[self.prompt_index] = self.explorer.get_prompt()
            self.query_one("#results", Static).update(self._render_prompt())
            self._refresh_table()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Token Explorer Application')
    parser.add_argument('--input', '-i', type=str, help='Path to input text file')
    parser.add_argument('--precompile', '-p', action='store_true', help='Precompile regex structs')
    parser.add_argument('--mode', '-m', type=str, choices=['fAIrytale', 'LLMTimes'], default='fAIrytale',
        help='Execution mode (e.g. fAIrytale, LLMTimes')
    args = parser.parse_args()

    if args.input:
        try:
            with open(args.input, 'r') as f:
                prompt = f.read()
        except FileNotFoundError:
            print(f"Error: Could not find input file '{args.input}'")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)
    app = TokenExplorer(args.mode, args.precompile)

    app.run()
