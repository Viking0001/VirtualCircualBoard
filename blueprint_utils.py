"""
VCB Blueprint Generator - OFICIÁLNÍ SPECIFIKACE
Knihovna pro generování blueprintů podle oficiální VCB specifikace

Formát:
- Prefix: "VCB+"
- Encoding: Base64
- Byte order: BIG-ENDIAN
- Komprese: ZSTD
"""

import base64
import struct
import io
import hashlib
from typing import Dict, Tuple, Optional
from enum import Enum
import numpy as np

try:
    import zstandard as zstd
except ImportError:
    raise ImportError("Nainstalujte zstandard: pip install zstandard")


class ComponentType(Enum):
    """Definice komponent a jejich RGBA hodnot"""
    WRITE = (77, 56, 62, 255)
    READ = (46, 71, 93, 255)
    CROSS = (102, 120, 142, 255)
    TUNNEL = (83, 85, 114, 255)
    MESH = (100, 106, 87, 255)
    BUS_0 = (122, 47, 36, 255)
    BUS_1 = (62, 122, 36, 255)
    BUS_2 = (36, 65, 122, 255)
    BUS_3 = (37, 98, 122, 255)
    BUS_4 = (122, 45, 102, 255)
    BUS_5 = (122, 112, 36, 255)
    TC_GRAY = (42, 53, 65, 255)
    TC_WHITE = (159, 168, 174, 255)
    TC_RED = (161, 85, 94, 255)
    TC_ORANGE = (161, 108, 86, 255)
    TC_YELLOW_W = (161, 133, 86, 255)
    TC_YELLOW_C = (161, 152, 86, 255)
    TC_LEMON = (153, 161, 86, 255)
    TC_GREEN_W = (136, 161, 86, 255)
    TC_GREEN_C = (108, 161, 86, 255)
    TC_TURQUOISE = (86, 161, 141, 255)
    TC_BLUE_LIGHT = (86, 147, 161, 255)
    TC_BLUE = (86, 123, 161, 255)
    TC_BLUE_DARK = (86, 98, 161, 255)
    TC_PURPLE = (102, 86, 161, 255)
    TC_VIOLET = (135, 86, 161, 255)
    TC_PINK = (161, 85, 151, 255)
    BUFFER = (146, 255, 99, 255)
    AND = (255, 198, 99, 255)
    OR = (99, 242, 255, 255)
    XOR = (174, 116, 255, 255)
    NOT = (255, 98, 138, 255)
    NAND = (255, 162, 0, 255)
    NOR = (48, 217, 255, 255)
    XNOR = (166, 0, 255, 255)
    LATCH_ON = (99, 255, 159, 255)
    LATCH_OFF = (56, 77, 71, 255)
    CLOCK = (255, 0, 65, 255)
    LED = (255, 255, 255, 255)
    TIMER = (255, 103, 0, 255)
    RANDOM = (229, 255, 0, 255)
    BREAKPOINT = (224, 0, 0, 255)
    WIRELESS_0 = (255, 0, 191, 255)
    WIRELESS_1 = (255, 0, 175, 255)
    WIRELESS_2 = (255, 0, 159, 255)
    WIRELESS_3 = (255, 0, 143, 255)
    ANNOTATION = (58, 69, 81, 255)
    FILLER = (140, 171, 161, 255)
    NONE = (0, 0, 0, 0)
    
    @classmethod
    def from_rgba(cls, rgba: Tuple[int, int, int, int]) -> 'ComponentType':
        """Najde komponentu podle RGBA hodnoty"""
        for comp in cls:
            if comp.value == rgba:
                return comp
        raise ValueError(f"Neznámá komponenta s RGBA: {rgba}")
    
    @property
    def rgba(self) -> Tuple[int, int, int, int]:
        """Vrátí RGBA hodnotu komponenty"""
        return self.value


class VCBBlueprint:
    """
    Generátor VCB blueprintů podle oficiální specifikace
    
    Specifikace:
    - Prefix: "VCB+"
    - Base64 encoding
    - BIG-ENDIAN byte order
    - ZSTD komprese
    """
    
    # Defaultní verze (podle analýzy existujícího blueprintu)
    # VCB 1.0.? používá verzi (0, 0, 0) v blueprintech
    VERSION = (0, 0, 0)
    
    # Layer ID konstanty (podle specifikace)
    LAYER_LOGIC = 0      # Logic layer (POVINNÁ)
    LAYER_DECO_ON = 1    # Decoration On (volitelná, pokud použita, obě deco musí být)
    LAYER_DECO_OFF = 2   # Decoration Off (volitelná, pokud použita, obě deco musí být)
    
    # Text Block Data ID (podle specifikace)
    TEXT_NAME = 1024
    TEXT_DESCRIPTION = 1025
    TEXT_TAGS = 1026
    
    def __init__(self, width: int, height: int, 
                 name: str = "",
                 description: str = "",
                 tags: str = "",
                 version: Tuple[int, int, int] = None):
        """
        Inicializace blueprintu
        
        Args:
            width: Šířka blueprintu
            height: Výška blueprintu
            name: Název blueprintu (volitelné)
            description: Popis blueprintu (volitelné)
            tags: Tagy oddělené čárkami (volitelné)
            version: Verze formátu (default: 1.0.0)
        """
        self.width = width
        self.height = height
        self.name = name
        self.description = description
        self.tags = tags
        
        if version is not None:
            self.VERSION = version
        
        # Inicializace vrstev
        self.layers: Dict[int, np.ndarray] = {}
        
    def set_logic_layer(self, components: np.ndarray):
        """
        Nastaví Logic layer (POVINNÁ vrstva)
        
        Args:
            components: 2D numpy array s ComponentType hodnotami
        """
        if components.shape != (self.height, self.width):
            raise ValueError(
                f"Rozměry pole {components.shape} neodpovídají "
                f"blueprintu ({self.height}, {self.width})"
            )
        
        # Převod ComponentType na RGBA hodnoty
        rgba_array = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        for y in range(self.height):
            for x in range(self.width):
                comp = components[y, x]
                if isinstance(comp, ComponentType):
                    rgba_array[y, x] = comp.rgba
                else:
                    rgba_array[y, x] = ComponentType.NONE.rgba
        
        self.layers[self.LAYER_LOGIC] = rgba_array
    
    def set_deco_layers(self, deco_on: np.ndarray, deco_off: np.ndarray):
        """
        Nastaví decoration layers (OBĚ MUSÍ BÝT NASTAVENY SOUČASNĚ)
        
        Args:
            deco_on: 2D numpy array s RGBA hodnotami pro Deco On
            deco_off: 2D numpy array s RGBA hodnotami pro Deco Off
        """
        if deco_on.shape != (self.height, self.width, 4):
            raise ValueError(f"Deco On má špatné rozměry: {deco_on.shape}")
        if deco_off.shape != (self.height, self.width, 4):
            raise ValueError(f"Deco Off má špatné rozměry: {deco_off.shape}")
        
        self.layers[self.LAYER_DECO_ON] = deco_on.astype(np.uint8)
        self.layers[self.LAYER_DECO_OFF] = deco_off.astype(np.uint8)
        
    def filter_components(self, component_type: ComponentType) -> np.ndarray:
        """
        Filtruje komponenty daného typu
        
        Args:
            component_type: Typ komponenty k filtraci
            
        Returns:
            2D boolean numpy array (True = komponenta nalezena)
        """
        if self.LAYER_LOGIC not in self.layers:
            return np.zeros((self.height, self.width), dtype=bool)
        
        layer = self.layers[self.LAYER_LOGIC]
        target_rgba = component_type.rgba
        
        mask = np.all(layer == target_rgba, axis=2)
        return mask
    
    def _compress_data(self, data: bytes) -> bytes:
        """Zkomprimuje data pomocí ZSTD"""
        compressor = zstd.ZstdCompressor(level=3)
        return compressor.compress(data)
    
    def _write_layer_block(self, buffer: io.BytesIO, layer_id: int, layer_data: np.ndarray):
        """
        Zapíše jeden layer blok do bufferu
        
        Formát (BIG-ENDIAN):
        - 4B: Block size
        - 4B: Layer ID
        - 4B: Uncompressed buffer size
        - N bytes: ZSTD compressed RGBA8 buffer
        """
        raw_data = layer_data.tobytes()
        compressed_data = self._compress_data(raw_data)
        
        # Block size = 4 (block_size) + 4 (layer_id) + 4 (uncompressed_size) + compressed_data
        block_size = 4 + 4 + 4 + len(compressed_data)
        
        # BIG-ENDIAN zápis ('>I' = unsigned int, big-endian)
        buffer.write(struct.pack('>I', block_size))
        buffer.write(struct.pack('>I', layer_id))
        buffer.write(struct.pack('>I', len(raw_data)))
        buffer.write(compressed_data)
    
    def _write_text_block(self, buffer: io.BytesIO, data_id: int, text: str):
        """
        Zapíše textový blok do bufferu
        
        Formát (BIG-ENDIAN):
        - 4B: Block size
        - 4B: Data ID (Name=1024, Description=1025, Tags=1026)
        - 4B: Uncompressed buffer size
        - N bytes: ZSTD compressed UTF-8 buffer
        """
        if not text:
            return  # Přeskočit prázdné textové bloky
            
        text_bytes = text.encode('utf-8')
        compressed_data = self._compress_data(text_bytes)
        
        # Block size = 4 (block_size) + 4 (data_id) + 4 (uncompressed_size) + compressed_data
        block_size = 4 + 4 + 4 + len(compressed_data)
        
        # BIG-ENDIAN zápis
        buffer.write(struct.pack('>I', block_size))
        buffer.write(struct.pack('>I', data_id))
        buffer.write(struct.pack('>I', len(text_bytes)))
        buffer.write(compressed_data)
    
    def _calculate_checksum(self, data: bytes) -> bytes:
        """
        Vypočítá 6-byte checksum (truncated SHA-1)
        
        DŮLEŽITÉ: Podle specifikace se checksum počítá z "remaining characters 
        of the blueprint string" - to znamená z BASE64 řetězce, ne binárních dat!
        
        Args:
            data: Binární data pro checksum (všechno po checksum poli)
            
        Returns:
            První 6 bytů SHA-1 hashe
        """
        # Převod dat na base64 (bez VCB+ prefixu)
        b64_data = base64.b64encode(data).decode('ascii')
        
        # SHA-1 z base64 řetězce
        sha1 = hashlib.sha1(b64_data.encode('ascii')).digest()
        return sha1[:6]  # Prvních 6 bytů
    
    def generate(self) -> str:
        """
        Vygeneruje blueprint jako base64 řetězec
        
        Returns:
            Base64 řetězec začínající 'VCB+'
        """
        # Validace: Logic layer musí být přítomna
        if self.LAYER_LOGIC not in self.layers:
            raise ValueError(
                "Logic layer musí být nastavena! "
                "Použijte set_logic_layer()"
            )
        
        # DŮLEŽITÉ: VCB vždy vyžaduje všechny 3 vrstvy (Logic, Deco On, Deco Off)
        # Pokud decoration vrstvy nejsou nastaveny, vytvoříme prázdné
        if self.LAYER_DECO_ON not in self.layers:
            # Prázdná decoration vrstva (všechny pixely průhledné)
            empty_deco = np.zeros((self.height, self.width, 4), dtype=np.uint8)
            self.layers[self.LAYER_DECO_ON] = empty_deco
            self.layers[self.LAYER_DECO_OFF] = empty_deco.copy()
        
        # === Příprava dat (bez checksum) ===
        temp_buffer = io.BytesIO()
        
        # Šířka a výška (BIG-ENDIAN)
        temp_buffer.write(struct.pack('>I', self.width))
        temp_buffer.write(struct.pack('>I', self.height))
        
        # Layer bloky (v pořadí: Logic, Deco On, Deco Off)
        for layer_id in [self.LAYER_LOGIC, self.LAYER_DECO_ON, self.LAYER_DECO_OFF]:
            if layer_id in self.layers:
                self._write_layer_block(temp_buffer, layer_id, self.layers[layer_id])
        
        # Text bloky (volitelné)
        if self.name:
            self._write_text_block(temp_buffer, self.TEXT_NAME, self.name)
        if self.description:
            self._write_text_block(temp_buffer, self.TEXT_DESCRIPTION, self.description)
        if self.tags:
            self._write_text_block(temp_buffer, self.TEXT_TAGS, self.tags)
        
        # Data pro checksum (všechno po checksum)
        data_after_checksum = temp_buffer.getvalue()
        
        # === Finální buffer s checksumem ===
        final_buffer = io.BytesIO()
        
        # Verze (3 bytes)
        final_buffer.write(struct.pack('BBB', *self.VERSION))
        
        # Checksum (6 bytes) - vypočítáno z dat po checksum
        checksum = self._calculate_checksum(data_after_checksum)
        final_buffer.write(checksum)
        
        # Zbytek dat
        final_buffer.write(data_after_checksum)
        
        # === Base64 encoding ===
        raw_bytes = final_buffer.getvalue()
        b64_string = base64.b64encode(raw_bytes).decode('ascii')
        
        return 'VCB+' + b64_string
    
    def get_stats(self) -> Dict:
        """Vrátí statistiky blueprintu"""
        stats = {
            'width': self.width,
            'height': self.height,
            'version': self.VERSION,
            'num_layers': len(self.layers),
            'total_pixels': self.width * self.height,
            'has_logic': self.LAYER_LOGIC in self.layers,
            'has_deco': self.LAYER_DECO_ON in self.layers,
        }
        
        if self.LAYER_LOGIC in self.layers:
            layer = self.layers[self.LAYER_LOGIC]
            non_empty = np.any(layer != (0, 0, 0, 0), axis=2)
            stats['num_components'] = int(np.sum(non_empty))
        
        return stats


# Pomocné funkce

def create_simple_blueprint(components: np.ndarray, 
                           name: str = "",
                           description: str = "",
                           tags: str = "",
                           version: Tuple[int, int, int] = (0, 0, 0)) -> str:
    """
    Vytvoří blueprint z 2D pole komponent
    
    Args:
        components: 2D numpy array s ComponentType hodnotami
        name: Název blueprintu (volitelné)
        description: Popis (volitelné)
        tags: Tagy (volitelné)
        version: Verze formátu (default: 0.0.0 - podle VCB 1.0.?)
        
    Returns:
        Base64 blueprint řetězec začínající 'VCB+'
    """
    height, width = components.shape
    bp = VCBBlueprint(width, height, name, description, tags, version)
    bp.set_logic_layer(components)
    return bp.generate()


def read_blueprint_info(blueprint_string: str, verbose: bool = False) -> Dict:
    """
    Načte základní informace z blueprint řetězce
    
    Args:
        blueprint_string: Blueprint řetězec začínající 'VCB+'
        verbose: Pokud True, vypíše detailní analýzu
        
    Returns:
        Slovník s informacemi o blueprintu
    """
    if not blueprint_string.startswith('VCB+'):
        raise ValueError("Blueprint musí začínat 'VCB+'")
    
    # Dekódování base64
    b64_data = blueprint_string[4:]
    raw_data = base64.b64decode(b64_data)
    
    if verbose:
        print(f"\nDETAILNÍ ANALÝZA BLUEPRINTU:")
        print(f"Celková délka: {len(raw_data)} bytů")
        print(f"Prvních 20 bytů (hex): {raw_data[:20].hex()}")
    
    buffer = io.BytesIO(raw_data)
    
    # Čtení hlavičky (BIG-ENDIAN)
    version = struct.unpack('BBB', buffer.read(3))
    checksum = buffer.read(6)
    width, height = struct.unpack('>II', buffer.read(8))
    
    if verbose:
        print(f"\nHLAVIČKA:")
        print(f"  Verze: {version}")
        print(f"  Checksum: {checksum.hex()}")
        print(f"  Rozměry: {width}x{height}")
        print(f"\nBLOKY:")
    
    # Čtení bloků
    blocks = []
    block_num = 0
    while buffer.tell() < len(raw_data):
        block_start = buffer.tell()
        block_size_bytes = buffer.read(4)
        if len(block_size_bytes) < 4:
            break
        
        block_size = struct.unpack('>I', block_size_bytes)[0]
        block_id = struct.unpack('>I', buffer.read(4))[0]
        uncompressed_size = struct.unpack('>I', buffer.read(4))[0]
        
        compressed_data_size = block_size - 12  # block_size includes all headers
        compressed_data = buffer.read(compressed_data_size)
        
        blocks.append({
            'block_num': block_num,
            'block_size': block_size,
            'block_id': block_id,
            'uncompressed_size': uncompressed_size,
            'compressed_size': len(compressed_data)
        })
        
        if verbose:
            print(f"  Blok #{block_num}:")
            print(f"    Block size: {block_size}")
            print(f"    Block ID: {block_id}")
            print(f"    Uncompressed size: {uncompressed_size}")
            print(f"    Compressed size: {len(compressed_data)}")
        
        block_num += 1
    
    return {
        'version': version,
        'width': width,
        'height': height,
        'checksum': checksum.hex(),
        'blocks': blocks
    }