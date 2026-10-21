"""A barreira de cobertura não pode aprovar um relatório incompleto."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'tools/quality.py'
spec=importlib.util.spec_from_file_location('quality_gate',path)
quality=importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


class QualityGateTests(unittest.TestCase):
    def report(self):
        return {'files':{f'src/svz/{name}':{'summary':{
            'num_branches':10,'percent_covered':100,'missing_lines':0,'missing_branches':0}}
            for name in quality.COVERAGE_FLOORS}}

    def test_complete_report_passes(self):
        self.assertEqual(len(quality.coverage_gate(self.report())),3)

    def test_missing_module_rejected(self):
        report=self.report(); report['files'].pop('src/svz/snapshot.py')
        with self.assertRaisesRegex(ValueError,'ausente'): quality.coverage_gate(report)

    def test_global_average_cannot_hide_low_module_coverage(self):
        report=self.report()
        report['files']['src/svz/projectile_combat.py']['summary']['percent_covered']=94.99
        with self.assertRaisesRegex(ValueError,'abaixo'): quality.coverage_gate(report)

    def test_line_only_coverage_rejected(self):
        report=self.report()
        report['files']['src/svz/projectile_combat.py']['summary']['num_branches']=0
        with self.assertRaisesRegex(ValueError,'ramos'): quality.coverage_gate(report)
