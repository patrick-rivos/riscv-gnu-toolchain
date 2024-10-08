from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
import re
import pytest
import sys

scripts_path = Path(__file__).parent.parent.parent.parent / "scripts"
sys.path.append(str(scripts_path))

from parse_build_warnings import parse_build_warnings, construct_warning_set, parse_build_warnings_from_directory, parse_target, POST_COMMIT, PRE_COMMIT, export_build_warnings

@pytest.fixture
def build_warning_string_1()->str:
    return '''../../../gcc/gcc/analyzer/analyzer.cc:248:25: warning: unknown conversion type character ‘@’ in format [-Wformat=]
  248 |       pp_printf (&pp, "%@", &event_id);
      |                         ^

'''

@pytest.fixture
def build_warning_string_2()->str:
    return '''../../../gcc/gcc/analyzer/analyzer.cc:248:25: warning: unknown conversion type character ‘@’ in format [-Wformat=]
  248 |       pp_printf (&pp, "%@", &event_id);
      |                         ^
In file included from ../../../gcc/gcc/analyzer/access-diagram.cc:35:
../../../gcc/gcc/analyzer/access-diagram.cc: In member function ‘virtual text_art::table ana::valid_region_spatial_item::make_table(const ana::bit_to_table_map&, text_art::style_manager&) const’:
../../../gcc/gcc/analyzer/access-diagram.cc:1509:35: warning: unknown conversion type character ‘@’ in format [-Wformat=]
 1509 |      s = fmt_styled_string (sm, _("buffer allocated on heap at %@"),
../../../gcc/gcc/intl.h:40:26: note: in definition of macro ‘gettext’
   40 | # define gettext(msgid) (msgid)
      |                          ^~~~~
../../../gcc/gcc/analyzer/access-diagram.cc:1509:33: note: in expansion of macro ‘_’
 1509 |      s = fmt_styled_string (sm, _("buffer allocated on heap at %@"),
      |                                 ^

'''

@pytest.fixture
def build_warning_string_3()->str:
    return '''libtool: install: warning: remember to run `libtool --finish /home/runner/work/gcc-postcommit-ci/gcc-postcommit-ci/riscv-gnu-toolchain/build/libexec/gcc/riscv64-unknown-linux-gnu/15.0.0'                    ^
../../../gcc/gcc/analyzer/analyzer.cc:248:25: warning: unknown conversion type character ‘@’ in format [-Wformat=]
  248 |       pp_printf (&pp, "%@", &event_id);
      |

'''

@pytest.fixture
def build_warning_string_4()->str:
    return '''libtool: install: warning: remember to run `libtool --finish /home/runner/work/gcc-postcommit-ci/gcc-postcommit-ci/riscv-gnu-toolchain/build/libexec/gcc/riscv64-unknown-linux-gnu/15.0.0'                    ^
plural.y:52.1-7: warning: POSIX Yacc does not support %expect [-Wyacc]
   52 | %expect 7
      | ^~~~~~~
../Rules:360: warning: overriding recipe for target '/home/runner/work/gcc-postcommit-ci/gcc-postcommit-ci/riscv-gnu-toolchain/build/build-glibc-linux-rv64gc_zba_zbb_zbc_zbs-lp64d/string/tst-strerror.out'

'''

@pytest.fixture
def build_warning_1(build_warning_string_1:str)->str:
    tmp=NamedTemporaryFile()
    tmp.write(build_warning_string_1.encode('utf-8'))
    tmp.seek(0)
    yield tmp.name
    tmp.close()
    

@pytest.fixture
def build_warning_2(build_warning_string_2 : str)->str:
    tmp=NamedTemporaryFile()
    tmp.write(build_warning_string_2.encode('utf-8'))
    tmp.seek(0)
    yield tmp.name
    tmp.close()

@pytest.fixture
def build_warnings_directory_1(build_warning_string_1, build_warning_string_3)->tuple[str, Path, Path]:
    tmp_dir = TemporaryDirectory()
    tmp_dir_path = Path(tmp_dir.name)

    build_1_path = tmp_dir_path / "linux-rv64gc-lp64d-a-non-multilib-build-log-stderr.log"
    with open(build_1_path, "w") as f:
        f.write(build_warning_string_1)
    build_2_path = tmp_dir_path / "newlib-rv32gc-lp64d-b-non-multilib-build-log-stderr.log"
    with open(build_2_path, "w") as f:
        f.write(build_warning_string_3)
        
    yield tmp_dir.name, build_1_path, build_2_path
    tmp_dir.cleanup()

@pytest.fixture
def build_warnings_directory_2(build_warning_string_2, build_warning_string_4)->tuple[str, Path, Path]:
    tmp_dir = TemporaryDirectory()
    tmp_dir_path = Path(tmp_dir.name)

    build_1_path = tmp_dir_path / "linux-rv64gc-lp64d-c-non-multilib-build-log-stderr.log"
    with open(build_1_path, "w") as f:
        f.write(build_warning_string_2)
    build_2_path = tmp_dir_path / "newlib-rv32gc-lp64d-c-non-multilib-build-log-stderr.log"
    with open(build_2_path, "w") as f:
        f.write(build_warning_string_4)

    yield tmp_dir.name, build_1_path, build_2_path
    tmp_dir.cleanup()

@pytest.fixture
def build_warnings_directory_3(build_warning_string_2, build_warning_string_4)->tuple[str, Path, Path]:
    tmp_dir = TemporaryDirectory()
    tmp_dir_path = Path(tmp_dir.name)

    build_1_path = tmp_dir_path / "c-linux-rv64gc-lp64d-non-multilib-build-log-stderr.log"
    with open(build_1_path, "w") as f:
        f.write(build_warning_string_2)
    build_2_path = tmp_dir_path / "c-newlib-rv32gc-lp64d-non-multilib-build-log-stderr.log"
    with open(build_2_path, "w") as f:
        f.write(build_warning_string_4)

    yield tmp_dir.name, build_1_path, build_2_path
    tmp_dir.cleanup()


def test_construct_warning_set_1(build_warning_1):
    warning_set = construct_warning_set(build_warning_1)
    expected = {'../../../gcc/gcc/analyzer/analyzer.cc:248:25: warning: unknown conversion type character ‘@’ in format [-Wformat=]\n  248 |       pp_printf (&pp, "%@", &event_id);\n      |                         ^\n'}
    assert(warning_set == expected)

def test_construct_warning_set_2(build_warning_2):
    warning_set = construct_warning_set(build_warning_2)
    expected ={'../../../gcc/gcc/analyzer/analyzer.cc:248:25: warning: unknown conversion type character ‘@’ in format [-Wformat=]\n  248 |       pp_printf (&pp, "%@", &event_id);\n      |                         ^\n', '../../../gcc/gcc/analyzer/access-diagram.cc:1509:35: warning: unknown conversion type character ‘@’ in format [-Wformat=]\n 1509 |      s = fmt_styled_string (sm, _("buffer allocated on heap at %@"),\n../../../gcc/gcc/intl.h:40:26: note: in definition of macro ‘gettext’\n   40 | # define gettext(msgid) (msgid)\n      |                          ^~~~~\n../../../gcc/gcc/analyzer/access-diagram.cc:1509:33: note: in expansion of macro ‘_’\n 1509 |      s = fmt_styled_string (sm, _("buffer allocated on heap at %@"),\n      |                                 ^\n'}
    assert(warning_set == expected)

def test_parse_build_warnings(build_warning_1, build_warning_2):
    new_warnings, resolved_warnings = parse_build_warnings(build_warning_1, build_warning_2)
    expected = {'../../../gcc/gcc/analyzer/access-diagram.cc:1509:35: warning: unknown conversion type character ‘@’ in format [-Wformat=]\n 1509 |      s = fmt_styled_string (sm, _("buffer allocated on heap at %@"),\n../../../gcc/gcc/intl.h:40:26: note: in definition of macro ‘gettext’\n   40 | # define gettext(msgid) (msgid)\n      |                          ^~~~~\n../../../gcc/gcc/analyzer/access-diagram.cc:1509:33: note: in expansion of macro ‘_’\n 1509 |      s = fmt_styled_string (sm, _("buffer allocated on heap at %@"),\n      |                                 ^\n'}
    assert(new_warnings == expected)
    assert(resolved_warnings == set())

def test_pre_commit_parse_build_warnings_from_directory(build_warnings_directory_1, build_warnings_directory_3):
    old_build_dir, old_a, old_b = build_warnings_directory_1
    new_build_dir, _, _ = build_warnings_directory_3
    a_target = parse_target(old_a.name)
    b_target = parse_target(old_b.name)

    new_expected = {a_target:set(), b_target: set()}
    new_expected[b_target].add("../Rules:360: warning: overriding recipe for target 'riscv-gnu-toolchain/build/build-glibc-linux-rv64gc_zba_zbb_zbc_zbs-lp64d/string/tst-strerror.out'\n")
    new_expected[b_target].add('''plural.y:52.1-7: warning: POSIX Yacc does not support %expect [-Wyacc]
   52 | %expect 7
      | ^~~~~~~\n''')
    new_expected[a_target].add('''../../../gcc/gcc/analyzer/access-diagram.cc:1509:35: warning: unknown conversion type character ‘@’ in format [-Wformat=]
 1509 |      s = fmt_styled_string (sm, _("buffer allocated on heap at %@"),
../../../gcc/gcc/intl.h:40:26: note: in definition of macro ‘gettext’
   40 | # define gettext(msgid) (msgid)
      |                          ^~~~~
../../../gcc/gcc/analyzer/access-diagram.cc:1509:33: note: in expansion of macro ‘_’
 1509 |      s = fmt_styled_string (sm, _("buffer allocated on heap at %@"),
      |                                 ^\n''')
    resolved_expected = {a_target: set(), b_target: set()}
    resolved_expected[b_target].add('''../../../gcc/gcc/analyzer/analyzer.cc:248:25: warning: unknown conversion type character ‘@’ in format [-Wformat=]
  248 |       pp_printf (&pp, "%@", &event_id);
      |\n''')
    new_warnings, resolved_warnings = parse_build_warnings_from_directory(old_build_dir, new_build_dir, PRE_COMMIT)
    print("pre-commit test\n\n\n")
    for target, warning_set in new_expected.items():
        print("expected: ", warning_set)
        print("\n\nnew_warnings: ", new_warnings[target])
        assert(new_warnings[target] == warning_set)
    for target, warning_set in resolved_expected.items():
        print("expected: ", warning_set)
        print("\n\resolved_warnings: ", resolved_warnings[target])
        assert(resolved_warnings[target] == warning_set)

def test_post_commit_parse_build_warnings_from_directory(build_warnings_directory_1, build_warnings_directory_2):
    old_build_dir, old_a, old_b = build_warnings_directory_1
    new_build_dir, _, _ = build_warnings_directory_2
    a_target = parse_target(old_a.name)
    b_target = parse_target(old_b.name)

    expected = {a_target:set(), b_target: set()}
    expected[b_target].add("../Rules:360: warning: overriding recipe for target 'riscv-gnu-toolchain/build/build-glibc-linux-rv64gc_zba_zbb_zbc_zbs-lp64d/string/tst-strerror.out'\n")
    expected[b_target].add('''plural.y:52.1-7: warning: POSIX Yacc does not support %expect [-Wyacc]
   52 | %expect 7
      | ^~~~~~~\n''')
    expected[a_target].add('''../../../gcc/gcc/analyzer/access-diagram.cc:1509:35: warning: unknown conversion type character ‘@’ in format [-Wformat=]
 1509 |      s = fmt_styled_string (sm, _("buffer allocated on heap at %@"),
../../../gcc/gcc/intl.h:40:26: note: in definition of macro ‘gettext’
   40 | # define gettext(msgid) (msgid)
      |                          ^~~~~
../../../gcc/gcc/analyzer/access-diagram.cc:1509:33: note: in expansion of macro ‘_’
 1509 |      s = fmt_styled_string (sm, _("buffer allocated on heap at %@"),
      |                                 ^\n''')
    new_warnings, resolved_warnings = parse_build_warnings_from_directory(old_build_dir, new_build_dir, POST_COMMIT)
    print("post-commit test\n\n\n")
    for target, warning_set in expected.items():
        print("expected: ", warning_set)
        print("\n\nnew_warnings: ", new_warnings[target])
        assert(new_warnings[target] == warning_set)

def test_export_empty_build_warnings():
    empty_warnings_dict = {"foo": set()}
    warning_type = "New build warnings"
    with NamedTemporaryFile() as tmp:
        export_build_warnings(empty_warnings_dict, tmp.name, warning_type)
        with open(tmp.name, 'r') as f:
            assert(f.read() == f"{warning_type} doesn't exist")

def test_export_build_warnings():
    warnings_dict = {"foo": set("bar\n")}
    warning_type = "New build warnings"
    with NamedTemporaryFile() as tmp:
        export_build_warnings(warnings_dict, tmp.name, warning_type)
        with open(tmp.name, 'r') as f:
            assert(f.readline() == f"# {warning_type}\n")
