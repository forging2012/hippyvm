from testing.test_interpreter import BaseTestInterpreter
from hippy.error import FatalError
import pytest

class TestPyPyBridgeScope(BaseTestInterpreter):

    def test_embed_py_func(self):
        phspace = self.space
        output = self.run('''

$src = <<<EOD
def f(a, b):
    return sum([a, b])
EOD;

embed_py_func($src);

echo f(4, 7);

        ''')
        assert phspace.int_w(output[0]) == 11


    def test_embed_py_func_inside_php_func(self):
        phspace = self.space
        output = self.run('''

function make() {

    $src = <<<EOD
def f(a, b):
    return sum([a, b])
EOD;

    embed_py_func($src);
}

make();
echo f(5, 7);

        ''')
        assert phspace.int_w(output[0]) == 12


    def test_embed_py_func_resolve_var_outer(self):
        phspace = self.space
        output = self.run('''

function make() {

    $a = 2;

    $src = <<<EOD
def f(b):
    return sum([a, b])
EOD;

    embed_py_func($src);
}

make();
echo f(3);

        ''')
        assert phspace.int_w(output[0]) == 5


    # embed_php_func

    # XXX move
    # --
    def test_embed_php_func(self):
        phspace = self.space
        output = self.run('''

$pysrc = <<<EOD
def f():
    php_src = "function g(\$a, \$b) { return \$a + \$b; }"
    g = embed_php_func(php_src)
    print(type(g))
    return g(5, 4)
EOD;

embed_py_func($pysrc);
echo f();

        ''')
        assert phspace.int_w(output[0]) == 9

    # --
    def test_embed_php_func_not_polluting_php_global(self):
        phspace = self.space
        output = self.run('''

$pysrc = <<<EOD
def f():
    php_src = "function g(\$a, \$b) { return \$a + \$b; }"
    embed_php_func(php_src)
EOD;

embed_py_func($pysrc);
echo function_exists("g");

        ''')
        assert not phspace.is_true(output[0])

    def test_php_looks_into_lexical_scope(self):
        phspace = self.space
        output = self.run('''

$pysrc = <<<EOD
def f():
    x = 1
    php_src = "function g(\$a) { return \$a + \$x; }"
    g = embed_php_func(php_src)
    return g
EOD;

embed_py_func($pysrc);
$g = f();
echo $g(7);

        ''')
        assert phspace.int_w(output[0]) == 8

    def test_lookup_php_constant(self):
        phspace = self.space
        output = self.run('''
            define("x", 3);
            $pysrc = <<<EOD
            def f():
                return x
            EOD;
            embed_py_func($pysrc);
            echo(f());
        ''')
        assert phspace.int_w(output[0]) == 3

    # XXX test for looking up PHP function from python code
    # XXX test lookup up Python outer-outer scopes from PHP

    def test_transitive_scope_lookup(self):
        phspace = self.space
        output = self.run('''
        $x = 668;

        $src1 = <<<EOD
def f1():
    src2 = """
    function f2() {
        \$src3 = "def f3(): return x";
        embed_py_func(\$src3);
        return f3();
    }
    """
    f2 = embed_php_func(src2)
    return f2();
EOD;

    embed_py_func($src1);
    echo f1();

        ''')
        assert phspace.int_w(output[0]) == 668

    def test_increment_outer_php_scope_from_python(self):
        pytest.skip("BROKEN")
        phspace = self.space
        output = self.run('''
$x = 44;
$src = <<<EOD
def f():
    php_src = "function g() { return \$x; }"
    g = embed_php_func(php_src)
    x += 1
    return g()
EOD;
embed_py_func($src);

echo(f());
        ''')
        assert phspace.int_w(output[0]) == 45

    def test_php_sees_outer_py_functions(self):
        phspace = self.space
        output = self.run('''
$pysrc = <<<EOD
def f():
    def g(): return 42

    phsrc = "function h() { return g(); }"
    h = embed_php_func(phsrc)

    return h()
EOD;
embed_py_func($pysrc);
echo(f());
        ''')
        assert phspace.int_w(output[0]) == 42

    def test_php_cant_call_normal_python_objects(self):
        phspace = self.space
        with pytest.raises(FatalError):
            output = self.run('''
$pysrc = <<<EOD
def f():
    g = 42

    phsrc = "function h() { return g(); }"
    h = embed_php_func(phsrc)

    return h()
EOD;
embed_py_func($pysrc);
echo(f());
        ''')

    def test_python_calling_php_func(self):
        phspace = self.space
        output = self.run('''
        function f() {
            return "f";
        }

        $src = <<<EOD
        def test():
            return f()
        EOD;
        embed_py_func($src);

        echo(test()); ''')
        assert phspace.str_w(output[0]) == "f"

    def test_python_calling_php_func_case_insensitive(self):
        phspace = self.space
        output = self.run('''
        function F() {
            return "F";
        }

        $src = <<<EOD
        def test():
            return "%s %s" % (f(), F())
        EOD;
        embed_py_func($src);

        echo(test()); ''')
        assert phspace.str_w(output[0]) == "F F"

    def test_python_ref_php_class(self):
        phspace = self.space
        output = self.run('''
        $src = <<<EOD
        def ref():
            return C()
        EOD;

        embed_py_func($src);

        class C {
            function m() { return "c.m"; }
        }
        echo(ref()->m()); ''')
        assert phspace.str_w(output[0]) == "c.m"

    def test_python_lookup_php_attr(self):
        phspace = self.space
        output = self.run("""
            $src = <<<EOD
            def ref():
                return C(2).x
            EOD;
            embed_py_func($src);

            class C {
                public $x;
                function __construct($x) {
                    $this->x = $x;
                }
            }
            echo(ref());
        """)
        assert phspace.int_w(output[0]) == 2

    def test_python_lookup_missing_php_attr(self):
        pytest.skip("BROKEN")
        phspace = self.space
        output = self.run("""
            $src = <<<EOD
            def ref():
                return C().x
            EOD;
            embed_py_func($src);

            class C {}
            ref();
        """)
        assert phspace.int_w(output[0]) == 2

    def test_python_set_php_attr(self):
        phspace = self.space
        output = self.run("""
            $src = <<<EOD
            def ref(c):
                c.x = 3
            EOD;
            embed_py_func($src);

            class C {
                public $x;
                function __construct($x) {
                    $this->x = $x;
                }
            }
            $c = new C(2);
            ref($c);
            echo($c->x);
        """)
        assert phspace.int_w(output[0]) == 3

    def test_python_call_php_method(self):
        phspace = self.space
        output = self.run("""
            $src = <<<EOD
            def ref():
                return C().m()
            EOD;
            embed_py_func($src);

            class C {
                function m() { return "c.m"; }
            }
            echo(ref());
        """)
        assert phspace.str_w(output[0]) == "c.m"

    def test_python_call_php_method_case_insensitive(self):
        phspace = self.space
        output = self.run("""
            $src = <<<EOD
            def ref():
                return C().M()
            EOD;
            embed_py_func($src);

            class C {
                function M() { return "c.m"; }
            }
            echo(ref());
        """)
        assert phspace.str_w(output[0]) == "c.m"

    def test_python_referencing_dollardollar_var(self):
        output = self.run("""
            $a = "b";
            $$a = "c";

            $src = <<<EOD
            def ref():
                return b
            EOD;
            embed_py_func($src);
            echo(ref());
        """)
        assert self.space.str_w(output[0]) == "c"

    #
    # PHP importing Python
    #

    def test_import_py_mod_attr(self):
        import math
        phspace = self.space
        output = self.run('''
        $math = import_py_mod("math");
        echo($math->pi);
        ''')
        assert phspace.float_w(output[0]) == math.pi
   
    def test_import_py_nested1_mod_func(self):
        phspace = self.space
        output = self.run('''
        $os_path = import_py_mod("os.path");
        echo($os_path->join("a", "b"));
        ''')
        assert phspace.str_w(output[0]) == "a/b"

    def test_import_py_nested2_mod_func(self):
        phspace = self.space
        output = self.run('''
        $os = import_py_mod("os");
        echo($os->path->join("a", "b"));
        ''')
        assert phspace.str_w(output[0]) == "a/b"



    #
    # Python importing PHP
    #

    def test_import_global_php_ns(self):
        phspace = self.space
        output = self.run('''
            $src = <<<EOD
            def test():
                php = php_global_ns()
                return php.strlen("test")
            EOD;
            embed_py_func($src);
            echo(test());
        ''')
        assert phspace.int_w(output[0]) == 4