# SPDX-License-Identifier: BSD-3-Clause
# Depthcharge: <https://github.com/nccgroup/depthcharge>
#
# pylint: disable=missing-function-docstring,missing-module-docstring

from unittest import TestCase

from depthcharge.checker import SecurityRisk, SecurityImpact


class TestSecurityRisk(TestCase):
    """
    Unit tests for depthcharge.checker.security_risk
    """

    def test_construtor_and_properties(self):
        impact = SecurityImpact.RD_MEM | SecurityImpact.WR_MEM

        risk = SecurityRisk(identifier='ident',
                            summary='summary',
                            impact=impact,
                            source='src',
                            description='description',
                            recommendation='recommendation')

        self.assertEqual(risk.identifier, 'ident')
        self.assertEqual(risk.impact, impact)
        self.assertEqual(risk.source, 'src')
        self.assertEqual(risk.description, 'description')
        self.assertEqual(risk.recommendation, 'recommendation')

    def test_from_dict(self):
        sr_dict = {
            'identifier': 'test-ident',
            'summary': 'test-summary',
            'impact': SecurityImpact.WEAK_AUTH,
            'source': 'test-src',
            'description': 'test-desc',
            'recommendation': 'test-rec'
        }

        risk = SecurityRisk.from_dict(sr_dict)
        risk.source += 'x'  # Writable property

        self.assertEqual(risk.identifier, 'test-ident')
        self.assertEqual(risk.summary, 'test-summary')
        self.assertEqual(risk.impact, SecurityImpact.WEAK_AUTH)
        self.assertEqual(risk.source, 'test-srcx')
        self.assertEqual(risk.description, 'test-desc')
        self.assertEqual(risk.recommendation, 'test-rec')
