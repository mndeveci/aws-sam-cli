from unittest import TestCase
from unittest.mock import Mock, patch

from samcli.lib.build.build_graph import BuildGraph, FunctionBuildDefinition, LayerBuildDefinition
from samcli.lib.build.build_strategy import ParallelBuildStrategy, BuildStrategy


class BuildStrategyTest(TestCase):
    pass


class DefaultBuildStrategyTest(TestCase):
    pass


class CachedBuildStrategyTest(TestCase):
    pass


class ParallelBuildStrategyTest(TestCase):

    @patch("samcli.lib.build.build_graph.BuildGraph._write")
    @patch("samcli.lib.build.build_graph.BuildGraph._read")
    def test(self, persist_mock, read_mock):
        build_graph = BuildGraph("build_dir")
        function_build_definition1 = FunctionBuildDefinition("runtime", "codeuri", {})
        function_build_definition2 = FunctionBuildDefinition("runtime2", "codeuri", {})
        build_graph.put_function_build_definition(function_build_definition1, Mock())
        build_graph.put_function_build_definition(function_build_definition2, Mock())

        layer_build_definition1 = LayerBuildDefinition("layer1", "codeuri", "build_method", [])
        layer_build_definition2 = LayerBuildDefinition("layer2", "codeuri", "build_method", [])
        build_graph.put_layer_build_definition(layer_build_definition1, Mock())
        build_graph.put_layer_build_definition(layer_build_definition2, Mock())

        delegate_build_strategy = Mock(wraps=BuildStrategy())
        delegate_build_strategy.build_single_function_definition.side_effect = [
            {
                "function1": "build_location1"
            },
            {
                "function2": "build_location2"
            }
        ]
        delegate_build_strategy.build_single_layer_definition.side_effect = [
            {
                "layer1": "build_location1"
            },
            {
                "layer2": "build_location2"
            }
        ]

        expected_result = {}
        for function_result in delegate_build_strategy.build_single_function_definition.side_effect:
            expected_result.update(function_result)
        for layer_result in delegate_build_strategy.build_single_layer_definition.side_effect:
            expected_result.update(layer_result)

        parallel_build_strategy = ParallelBuildStrategy(build_graph, delegate_build_strategy)
        result = parallel_build_strategy.build()

        self.assertEqual(result, expected_result)
