import subprocess
import shutil
import os
import cups

class Layouter:
    """
    Class that combines standalone image, text and headline into a formatted pdf and prints
    """

    def __init__(self, index):
        self.index = index  # combination of prompt index and timestamp

    def formatter(self):
        """
        Combines standalone image, text and headline into a formatted pdf
        """
        self.update_variable()
        self.execute_latex()

    def update_variable(self):
        """
        Set correct file index references in variable.txt file
        """
        headline = f"\\newcommand{{\\faryTitle}}{{../../data/{self.index}_headline.txt}}"
        story = f"\\newcommand{{\\story}}{{../../data/{self.index}_story.txt}}"
        image = f"\\newcommand{{\\faryPicture}}{{../../data/{self.index}_image.png}}"

        with open("variable.txt", "w") as file:
            file.write(headline + "\n")
            file.write(story + "\n")
            file.write(image + "\n")

    def execute_latex(self):
        """
        Execute the latex main.tex and store as pdf
        """
        tex_file = "main.tex"
        output_dir = "../../data/pdf"
        pdf_name = f"{self.index}.pdf"
        subprocess.run(["pdflatex", f"-output-directory={output_dir}", tex_file], check=True)

        # Change name of PDF file
        base_pdf_name = os.path.splitext(os.path.basename(tex_file))[0] + ".pdf"
        generated_pdf_path = os.path.join(output_dir, base_pdf_name)
        final_pdf_path = os.path.join(output_dir, pdf_name)

        shutil.move(generated_pdf_path, final_pdf_path)


    def printer(self, copies=2, printer_name=cups.Connection().getDefault()):
        """
        Prints final pdf
        """
        command = ['lp', '-n', str(copies), f'../../data/pdf/{self.index}.pdf']
        if printer_name:
            command += ['-d', printer_name]
            subprocess.run(command)

if __name__ == "__main__":
    x = Layouter('test')
    x.formatter()
    x.printer(printer_name = cups.Connection().getDefault())

