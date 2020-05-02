import unittest, graderunittest

class TestHelloPython(unittest.TestCase):

    def test_import(self):
        """Import the functions module (1p)"""
        import functions

    def test_function(self):
        """Check hello function exists (1p)"""
        import functions
        def protofunction():
            pass
        self.assertTrue(type(functions.hello), type(protofunction))

    def test_return(self):
        """Check hello function return value (3p)"""
        import functions
        self.assertEqual(functions.hello(), "Hello Python!")

if __name__ == '__main__':
    unittest.main(testRunner=graderunittest.PointsTestRunner(verbosity=2))
