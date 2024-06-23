
import os
import warnings
import matplotlib.pyplot as plt


class TextImageRenderer:
    def __init__(self, output_dir):
        assert output_dir is not None
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir

    @classmethod
    def insert_line_breaks(cls, text):
        words = text.split()
        output = ""
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 > 80:
                output += current_line + "\n"
                current_line = word
            else:
                if current_line:
                    # Add a space before the word if it's not the first word in the line
                    current_line += " "
                current_line += word
        # Add the last line if it exists
        if current_line:
            output += current_line
        return output

    def create_domain_image(self, fname, title, content):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.axis('off')
            title = title.replace('$', '**')
            content = content.replace('$', '**')
            content = '\n\n'.join([self.insert_line_breaks(cont) for cont in content.split('\n')])
            ax.text(0.5, 1.7, title, ha='center', va='top', fontsize=18, transform=ax.transAxes)
            ax.text(0.5, 1.4, content, ha='center', va='top', fontsize=10, transform=ax.transAxes)
            # Save the figure
            output_path = os.path.join(self.output_dir, f"{fname.replace('.', '__')}.png")
            plt.savefig(output_path, bbox_inches='tight')
            plt.close()

