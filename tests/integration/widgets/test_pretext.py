#-----------------------------------------------------------------------------
# Copyright (c) 2012 - 2022, Anaconda, Inc. All rights reserved.
#
# Powered by the Bokeh Development Team.
#
# The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Boilerplate
#-----------------------------------------------------------------------------
from __future__ import annotations # isort:skip

import pytest ; pytest

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------

# Standard library imports
from html import escape

# Bokeh imports
from bokeh.models import PreText
from tests.support.plugins.project import BokehModelPage
from tests.support.util.selenium import find_element_for

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------

pytest_plugins = (
    "tests.support.plugins.project",
)

text = """
Your <a href="https://en.wikipedia.org/wiki/HTML">HTML</a>-supported text is initialized with the <b>text</b> argument.  The
remaining div arguments are <b>width</b> and <b>height</b>. For this example, those values
are <i>200</i> and <i>100</i> respectively."""


@pytest.mark.selenium
class Test_PreText:
    def test_displays_div_as_text(self, bokeh_model_page: BokehModelPage) -> None:
        para = PreText(text=text)
        page = bokeh_model_page(para)

        el = find_element_for(page.driver, para, "div pre")
        assert el.get_attribute("innerHTML") == escape(text, quote=None)

        assert page.has_no_console_errors()

    def test_set_style(self, bokeh_model_page: BokehModelPage) -> None:
        para = PreText(text=text, style={'font-size': '26px'})
        page = bokeh_model_page(para)

        el = find_element_for(page.driver, para)
        assert 'font-size: 26px;' in el.get_attribute('style')

        assert page.has_no_console_errors()
