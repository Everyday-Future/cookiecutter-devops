
import colorsys


class Color:
    def __init__(self, value):
        if isinstance(value, str):
            # Parse strings as hex values
            self.value = self.parse_hex(value)
        elif isinstance(value, (list, tuple)):
            # Parse tuples as rgb or rgba values, which can be set directly
            self.value = value
        else:
            raise ValueError(f'Color() got unrecognized color value - {value}')

    @staticmethod
    def hex_to_rgb(hex_color: str):
        hex_color = hex_color.replace('#', '')
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return rgb

    @staticmethod
    def hex_to_rgba(hex_color: str):
        hex_color = hex_color.replace('#', '')
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4, 6))
        return rgb

    @classmethod
    def parse_hex(cls, hex_color: str):
        hex_color = hex_color.replace('#', '')
        if len(hex_color) == 6:
            return cls.hex_to_rgb(hex_color)
        elif len(hex_color) == 8:
            return cls.hex_to_rgba(hex_color)
        else:
            raise ValueError(f'parse_hex did not recognize hex format - {hex_color}')

    @classmethod
    def hex_to_hsv(cls, hex_color: str):
        rgb = cls.hex_to_rgb(hex_color)
        hsv = colorsys.rgb_to_hsv(*rgb)
        return hsv

    @classmethod
    def rgba_to_rgb(cls, rgba_color: tuple):
        if len(rgba_color) == 3:
            return rgba_color
        elif len(rgba_color) == 4:
            return rgba_color[0], rgba_color[1], rgba_color[2]
        else:
            raise ValueError(f"Unknown rgba value - {rgba_color}")

    @classmethod
    def rgb_to_hsv(cls, rgb_color: tuple):
        if len(rgb_color) == 4:
            rgb_color = cls.rgba_to_rgb(rgba_color=rgb_color)
        return colorsys.rgb_to_hsv(*rgb_color)

    @classmethod
    def rgb_to_hex(cls, rgb_color: tuple):
        return "#{0:02x}{1:02x}{2:02x}".format(*[int(r) for r in rgb_color]).upper()

    @classmethod
    def rgba_to_hex(cls, rgba_color: tuple):
        return "#{0:02x}{1:02x}{2:02x}{3:02x}".format(*[int(r) for r in rgba_color]).upper()

    @classmethod
    def hsv_to_rgb(cls, hsv_color: tuple):
        return colorsys.hsv_to_rgb(*hsv_color)

    @classmethod
    def hsv_to_hex(cls, hsv_color: tuple):
        rgb = cls.hsv_to_rgb(hsv_color)
        return cls.rgb_to_hex(rgb)
