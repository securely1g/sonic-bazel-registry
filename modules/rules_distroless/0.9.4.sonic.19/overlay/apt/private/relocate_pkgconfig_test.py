import unittest
from relocate_pkgconfig import relocate

class RelocationTest(unittest.TestCase):
    def test_installed_layouts(self):
        for directory, relative in [("usr/lib/x86_64-linux-gnu/pkgconfig", "../../.."), ("usr/lib/aarch64-linux-gnu/pkgconfig", "../../.."), ("usr/lib/pkgconfig", "../.."), ("usr/share/pkgconfig", "../..")]:
            raw = b"prefix=/usr\nlibdir=${prefix}/lib\nVersion: 9\nLibs: -lx\n"
            expected = b"prefix=${pcfiledir}/" + relative.encode() + b"\nlibdir=${prefix}/lib\nVersion: 9\nLibs: -lx\n"
            self.assertEqual(relocate(raw, directory + "/x.pc"), expected)
    def test_preserves_other_fields_and_line_endings(self):
        raw = b"# prefix=/usr\r\n prefix=/usr\r\ncustom_prefix=/usr\r\nprefix \t= /usr \t\r\nCflags: -Dprefix=/usr\r\n"
        self.assertEqual(relocate(raw, "usr/lib/pkgconfig/x.pc"), raw.replace(b"prefix \t= /usr \t", b"prefix \t= ${pcfiledir}/../.. \t"))
    def test_literal_standard_install_variables_without_prefix(self):
        raw = b"libdir=/usr/lib/aarch64-linux-gnu\nincludedir=/usr/include\nName: untouched\nLibs: -L${libdir} -lkeyutils\n"
        expected = b"libdir=${pcfiledir}/..\nincludedir=${pcfiledir}/../../../include\nName: untouched\nLibs: -L${libdir} -lkeyutils\n"
        self.assertEqual(relocate(raw, "usr/lib/aarch64-linux-gnu/pkgconfig/libkeyutils.pc"), expected)
    def test_literal_exec_prefix_and_install_directory_outside_pc_parent(self):
        raw = b"exec_prefix=/usr\nprefix=/opt/vendor\nVersion: 4\n"
        expected = b"exec_prefix=${pcfiledir}/../..\nprefix=${pcfiledir}/../../../opt/vendor\nVersion: 4\n"
        self.assertEqual(relocate(raw, "usr/lib/pkgconfig/vendor.pc"), expected)
    def test_preserves_variable_unrelated_and_missing_prefixes(self):
        for raw in [b"prefix=${pcfiledir}/../..\n", b"Name: x\n", b"prefix=/usr/../opt\n"]:
            self.assertEqual(relocate(raw, "usr/lib/pkgconfig/x.pc"), raw)

if __name__ == "__main__":
    unittest.main()
