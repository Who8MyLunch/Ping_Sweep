
from __future__ import division, print_function, unicode_literals

import os
import unittest

import ping_sweep

class Test_Ping_Sweep(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass


    def test_is_admin(self):
        """
        I don't know how to make a unit test for this tool without requiring the user to run the test
        as admin.  That won't be practical for someone in the future.

        TODO: find a better way to run this test.
        """
        val = ping_sweep.is_admin()
        msg = 'Must run this unit test ad admin or root.'

        self.assertTrue(val, msg)


    def test_invalid_address(self):
        with self.assertRaises(ping_sweep.PingSweepNameError) as cm:
            addr = 'asd.asd'
            sock = ping_sweep.create_socket(addr)

        value_true = "'Unable to create socket with name: {:s}'".format(addr)

        msg = 'Test for gracefully handling an invalid address.'
        self.assertEqual(cm.exception.msg, value_true)






    # def test_encode_uint16(self):
    #     data, meta = io.read(self.fname16)

    #     data_comp = jls.encode(data)

    #     self.assertTrue(data_comp.size == 2732889)



# Standalone.
if __name__ == '__main__':
    unittest.main(verbosity=2)
