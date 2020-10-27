from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock, call, ANY

from samcli.commands.build.exceptions import MissingBuildMethodException
from samcli.lib.build.build_graph import BuildGraph, FunctionBuildDefinition, LayerBuildDefinition
from samcli.lib.build.build_strategy import ParallelBuildStrategy, BuildStrategy, DefaultBuildStrategy


@patch("samcli.lib.build.build_graph.BuildGraph._write")
@patch("samcli.lib.build.build_graph.BuildGraph._read")
class BuildStrategyBaseTest(TestCase):

    def setUp(self):
        # create a build graph with 2 function definitions and 2 layer definitions
        self.build_graph = BuildGraph("build_dir")

        self.function1_1 = Mock()
        self.function1_2 = Mock()
        self.function2 = Mock()

        self.function_build_definition1 = FunctionBuildDefinition("runtime", "codeuri", {})
        self.function_build_definition1.functions = [self.function1_1, self.function1_2]
        self.function_build_definition2 = FunctionBuildDefinition("runtime2", "codeuri", {})
        self.function_build_definition1.functions = [self.function2]
        self.build_graph.put_function_build_definition(self.function_build_definition1, Mock())
        self.build_graph.put_function_build_definition(self.function_build_definition2, Mock())

        self.layer_build_definition1 = LayerBuildDefinition("layer1", "codeuri", "build_method", [])
        self.layer_build_definition2 = LayerBuildDefinition("layer2", "codeuri", "build_method", [])
        self.build_graph.put_layer_build_definition(self.layer_build_definition1, Mock())
        self.build_graph.put_layer_build_definition(self.layer_build_definition2, Mock())


class BuildStrategyTest(BuildStrategyBaseTest):

    def test_build_functions_layers(self):
        build_strategy = BuildStrategy(self.build_graph)

        self.assertEqual(build_strategy.build(), {})

    def test_build_functions_layers_mock(self):
        mock_build_strategy = BuildStrategy(self.build_graph)
        given_build_functions_result = {"function1": "build_dir_1"}
        given_build_layers_result = {"layer1": "layer_dir_1"}

        mock_build_strategy._build_functions = Mock(return_value=given_build_functions_result)
        mock_build_strategy._build_layers = Mock(return_value=given_build_layers_result)
        build_result = mock_build_strategy.build()

        expected_result = {}
        expected_result.update(given_build_functions_result)
        expected_result.update(given_build_layers_result)
        self.assertEqual(build_result, expected_result)

        mock_build_strategy._build_functions.assert_called_once_with(self.build_graph)
        mock_build_strategy._build_layers.assert_called_once_with(self.build_graph)

    def test_build_single_function_layer(self):
        mock_build_strategy = BuildStrategy(self.build_graph)
        given_build_functions_result = [{"function1": "build_dir_1"}, {"function2": "build_dir_2"}]
        given_build_layers_result = [{"layer1": "layer_dir_1"}, {"layer2": "layer_dir_2"}]

        mock_build_strategy.build_single_function_definition = Mock(side_effect=given_build_functions_result)
        mock_build_strategy.build_single_layer_definition = Mock(side_effect=given_build_layers_result)
        build_result = mock_build_strategy.build()

        expected_result = {}
        for function_result in given_build_functions_result:
            expected_result.update(function_result)
        for layer_result in given_build_layers_result:
            expected_result.update(layer_result)

        self.assertEqual(build_result, expected_result)

        # assert individual functions builds have been called
        mock_build_strategy.build_single_function_definition.assert_has_calls([
            call(self.function_build_definition1),
            call(self.function_build_definition2),
        ])

        # assert individual layer builds have been called
        mock_build_strategy.build_single_layer_definition.assert_has_calls([
            call(self.layer_build_definition1),
            call(self.layer_build_definition2),
        ])


@patch("samcli.lib.build.build_strategy.pathlib.Path")
@patch("samcli.lib.build.build_strategy.osutils.copytree")
class DefaultBuildStrategyTest(BuildStrategyBaseTest):

    def test_layer_build_should_fail_when_no_build_method_is_provided(self, mock_copy_tree, mock_path):
        given_layer = Mock()
        given_layer.build_method = None
        layer_build_definition = LayerBuildDefinition("layer1", "codeuri", "build_method", [])
        layer_build_definition.layer = given_layer

        build_graph = Mock(spec=BuildGraph)
        build_graph.get_layer_build_definitions.return_value = [layer_build_definition]
        build_graph.get_function_build_definitions.return_value = []
        default_build_strategy = DefaultBuildStrategy(build_graph, "build_dir", Mock(), Mock())

        self.assertRaises(MissingBuildMethodException, default_build_strategy.build)

    def test_build_layers_and_functions(self, mock_copy_tree, mock_path):
        given_build_function = Mock()
        given_build_layer = Mock()
        given_build_dir = "build_dir"
        default_build_strategy = DefaultBuildStrategy(self.build_graph,
                                                      given_build_dir,
                                                      given_build_function,
                                                      given_build_layer)

        default_build_strategy.build()

        # assert that build function has been called
        given_build_function.assert_has_calls([
            call(
                self.function_build_definition1.get_function_name(),
                self.function_build_definition1.codeuri,
                self.function_build_definition1.runtime,
                self.function_build_definition1.get_handler_name(),
                ANY,
                self.function_build_definition1.metadata
            ),
            call(
                self.function_build_definition2.get_function_name(),
                self.function_build_definition2.codeuri,
                self.function_build_definition2.runtime,
                self.function_build_definition2.get_handler_name(),
                ANY,
                self.function_build_definition2.metadata
            ),
        ])

        # assert that layer build function has been called
        given_build_layer.assert_has_calls([
            call(
                self.layer_build_definition1.layer.name,
                self.layer_build_definition1.layer.codeuri,
                self.layer_build_definition1.layer.build_method,
                self.layer_build_definition1.layer.compatible_runtimes,
            ),
            call(
                self.layer_build_definition2.layer.name,
                self.layer_build_definition2.layer.codeuri,
                self.layer_build_definition2.layer.build_method,
                self.layer_build_definition2.layer.compatible_runtimes,
            ),
        ])

        # assert that mock path has been called
        mock_path.assert_has_calls([
            call(given_build_dir, self.function_build_definition1.get_function_name()),
            call(given_build_dir, self.function_build_definition2.get_function_name()),
        ], any_order=True)

        # assert that function1_2 artifacts have been copied from already built function1_1
        mock_copy_tree.assert_called_with(
            str(mock_path(given_build_dir, self.function_build_definition1.get_function_name())),
            str(mock_path(given_build_dir, self.function1_2.name))
        )


class CachedBuildStrategyTest(TestCase):
    pass


class ParallelBuildStrategyTest(BuildStrategyBaseTest):

    def test_given_async_context_should_call_expected_methods(self):
        mock_async_context = Mock()
        delegate_build_strategy = MagicMock(wraps=BuildStrategy(self.build_graph))
        parallel_build_strategy = ParallelBuildStrategy(self.build_graph, delegate_build_strategy, mock_async_context)

        given_build_results = [
            {"function1": "function_location1"},
            {"function2": "function_location2"},
            {"layer1": "layer_location1"},
            {"layer2": "layer_location2"},
        ]
        mock_async_context.run_async.return_value = given_build_results

        results = parallel_build_strategy.build()

        expected_results = {}
        for given_build_result in given_build_results:
            expected_results.update(given_build_result)
        self.assertEqual(results, expected_results)

        # assert that result has collected
        mock_async_context.run_async.assert_has_calls([
            call()
        ])

        # assert that delegated function calls have been registered in async context
        mock_async_context.add_async_task.assert_has_calls([
            call(delegate_build_strategy.build_single_function_definition, self.function_build_definition1),
            call(delegate_build_strategy.build_single_function_definition, self.function_build_definition2),
            call(delegate_build_strategy.build_single_layer_definition, self.layer_build_definition1),
            call(delegate_build_strategy.build_single_layer_definition, self.layer_build_definition2),
        ])

    def test_given_delegate_strategy_it_should_call_delegated_build_methods(self):
        # create a mock delegate build strategy
        delegate_build_strategy = MagicMock(wraps=BuildStrategy(self.build_graph))
        delegate_build_strategy.build_single_function_definition.return_value = {
            "function1": "build_location1",
            "function2": "build_location2"
        }
        delegate_build_strategy.build_single_layer_definition.return_value = {
            "layer1": "build_location1",
            "layer2": "build_location2"
        }

        # create expected results
        expected_result = {}
        expected_result.update(delegate_build_strategy.build_single_function_definition.return_value)
        expected_result.update(delegate_build_strategy.build_single_layer_definition.return_value)

        # create build strategy with delegate
        parallel_build_strategy = ParallelBuildStrategy(self.build_graph, delegate_build_strategy)
        result = parallel_build_strategy.build()

        self.assertEqual(result, expected_result)

        # assert that delegate build strategy had been used with context
        delegate_build_strategy.__enter__.assert_called_once()
        delegate_build_strategy.__exit__.assert_called_once_with(ANY, ANY, ANY)

        # assert that delegate build strategy function methods have been called
        delegate_build_strategy.build_single_function_definition.assert_has_calls([
            call(self.function_build_definition1),
            call(self.function_build_definition2),
        ])

        # assert that delegate build strategy layer methods have been called
        delegate_build_strategy.build_single_layer_definition.assert_has_calls([
            call(self.layer_build_definition1),
            call(self.layer_build_definition2),
        ])
