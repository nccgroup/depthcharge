"""
The algorithm implemented in this file is derived from a public work
that does not appear to be released under any particular licenses.
(We will happily make corrections if the above is incorrect!)

Therefore, this file is regarded as public domain, to the fullest extent
permitted by applicable law.

The author(s) of Depthcharge make no claim of copyright of this file.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
# Keeping long URLs as-is. pylint: disable=line-too-long


def reverse_crc32_4bytes(crc: int,
                         poly=0xedb88320, invpoly=0x5b358fd3,
                         initxor=0xffffffff, finalxor=0xffffffff) -> int:
    """
    "Reverses" a CRC32 operation computed over a 4-byte (32-bit) input.

    This implementation  is just a simplification of Listing 6 from the
    following paper.  We're basically trying to compute a chosen CRC32 by
    "appending" 4 bytes to a zero-length input.

    Reversing CRC - Theory and Practice
    by Martin Stigge, Henryk Plötz, Wolf Müller, Jens-Peter Redlich
    HU Berlin Public Report, SAR-PR-2006-05, May 2006

    URL: https://sar.informatik.hu-berlin.de/research/publications/SAR-PR-2006-05/SAR-PR-2006-05_.pdf
         https://web.archive.org/web/20191010094138/https://sar.informatik.hu-berlin.de/research/publications/SAR-PR-2006-05/SAR-PR-2006-05_.pdf

    If `endianness` is set to None, an integer is returned. Otherwise, a bytes
    object is returned, converted per the specified `endianness` value.
    """
    tcrcreg = crc ^ finalxor
    data = 0
    for _ in range(0, 32):

        # Reduce modulo polynomial
        if data & 0x1:
            data = (data >> 1) ^ poly
        else:
            data >>= 1

        # Add inverse polynomial if corresponding bit of operand is set
        if tcrcreg & 0x1:
            data ^= invpoly

        tcrcreg >>= 1

    result = (data ^ initxor)
    return result
