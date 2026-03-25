"""Shared fake MATLAB engine classes for tests.

Each class simulates specific MATLAB engine behaviors needed by action tests.
Import from here instead of defining inline fakes in test files.
"""


class FakeScanEngine:
    """Fake engine for scan, highlight, and list_opened action tests.

    Supports find_system, bdroot, get_param (Handle, BlockType),
    and hilite_system with configurable failures.
    """

    def __init__(
        self,
        models,
        active_root,
        shallow_blocks,
        recursive_blocks,
        block_types,
        valid_handles=None,
        highlight_fail_targets=None,
    ):
        self.models = models
        self.active_root = active_root
        self.shallow_blocks = shallow_blocks
        self.recursive_blocks = recursive_blocks
        self.block_types = block_types
        self.valid_handles = set(valid_handles or [])
        self.highlight_fail_targets = set(highlight_fail_targets or [])
        self.highlight_calls = []

    def find_system(self, *args):
        if args == ("Type", "block_diagram"):
            return self.models

        scan_root = args[0]
        if "SearchDepth" in args:
            return self.shallow_blocks.get(scan_root, [scan_root])
        return self.recursive_blocks.get(scan_root, [scan_root])

    def bdroot(self):
        return self.active_root

    def get_param(self, block_path, param_name):
        if param_name == "BlockType":
            return self.block_types.get(block_path, "SubSystem")
        if param_name == "Handle":
            if self.valid_handles and block_path not in self.valid_handles:
                raise RuntimeError("not found")
            return 1
        raise RuntimeError(f"unsupported param {param_name}")

    def hilite_system(self, block_path, mode, nargout=0):
        self.highlight_calls.append((block_path, mode, nargout))
        if block_path in self.highlight_fail_targets:
            raise RuntimeError("highlight failed")
        return None


class FakeScanOutputEngine:
    """Minimal fake engine for scan output-controls tests.

    Returns a fixed model with 3 blocks, all typed as Gain.
    """

    def find_system(self, *args):
        if args == ("Type", "block_diagram"):
            return ["m1"]
        scan_root = args[0]
        return [scan_root, f"{scan_root}/C", f"{scan_root}/A", f"{scan_root}/B"]

    def bdroot(self):
        return "m1"

    def get_param(self, block_path, param_name):
        if param_name == "Handle":
            return 1
        if param_name == "BlockType":
            return "Gain"
        raise RuntimeError("unsupported")


class FakeConnectionsEngine:
    """Fake engine for connections action tests.

    Models a 3-block ring topology: A -> B -> C -> A.
    """

    def __init__(self):
        self.blocks = {"m1/A", "m1/B", "m1/C"}
        self.port_handles = {
            "m1/A": {"Inport": [14], "Outport": [11]},
            "m1/B": {"Inport": [21], "Outport": [22]},
            "m1/C": {"Inport": [31], "Outport": [32]},
        }
        self.port_line = {11: 1001, 14: 1003, 21: 1001, 22: 1002, 31: 1002, 32: 1003}
        self.line_meta = {
            1001: {"SrcPortHandle": 11, "DstPortHandle": [21], "Name": "sig_ab"},
            1002: {"SrcPortHandle": 22, "DstPortHandle": [31], "Name": "sig_bc"},
            1003: {"SrcPortHandle": 32, "DstPortHandle": [14], "Name": "sig_ca"},
        }
        self.port_parent = {
            11: "m1/A",
            14: "m1/A",
            21: "m1/B",
            22: "m1/B",
            31: "m1/C",
            32: "m1/C",
        }
        self.port_number = {11: 1, 14: 1, 21: 1, 22: 1, 31: 1, 32: 1}

    def get_param(self, target, param_name):
        if isinstance(target, str) and param_name == "Handle":
            if target not in self.blocks:
                raise RuntimeError("not found")
            return 1
        if isinstance(target, str) and param_name == "PortHandles":
            return self.port_handles[target]
        if isinstance(target, (int, float)):
            key = int(target)
            if param_name == "Line":
                return self.port_line.get(key, -1)
            if key in self.line_meta:
                return self.line_meta[key][param_name]
            if param_name == "Parent":
                return self.port_parent[key]
            if param_name == "PortNumber":
                return self.port_number[key]
        raise RuntimeError(f"unsupported param: {param_name}")


class FakeStrictMatlabHandleEngine:
    """Emulates MATLAB engine behavior that rejects Python int handles.

    Same ring topology as FakeConnectionsEngine, but all handles are floats
    and int handles raise RuntimeError (matching real MATLAB behavior).
    """

    def __init__(self):
        self.blocks = {"m1/A", "m1/B", "m1/C"}
        self.port_handles = {
            "m1/A": {"Inport": [14.0], "Outport": [11.0]},
            "m1/B": {"Inport": [21.0], "Outport": [22.0]},
            "m1/C": {"Inport": [31.0], "Outport": [32.0]},
        }
        self.port_line = {
            11: 1001.0,
            14: 1003.0,
            21: 1001.0,
            22: 1002.0,
            31: 1002.0,
            32: 1003.0,
        }
        self.line_meta = {
            1001: {"SrcPortHandle": 11.0, "DstPortHandle": [21.0], "Name": "sig_ab"},
            1002: {"SrcPortHandle": 22.0, "DstPortHandle": [31.0], "Name": "sig_bc"},
            1003: {"SrcPortHandle": 32.0, "DstPortHandle": [14.0], "Name": "sig_ca"},
        }
        self.port_parent = {
            11: "m1/A",
            14: "m1/A",
            21: "m1/B",
            22: "m1/B",
            31: "m1/C",
            32: "m1/C",
        }
        self.port_number = {11: 1.0, 14: 1.0, 21: 1.0, 22: 1.0, 31: 1.0, 32: 1.0}

    def get_param(self, target, param_name):
        if isinstance(target, str) and param_name == "Handle":
            if target not in self.blocks:
                raise RuntimeError("not found")
            return 1.0
        if isinstance(target, str) and param_name == "PortHandles":
            return self.port_handles[target]

        if isinstance(target, int):
            raise RuntimeError(
                "The first input to get_param must be of type 'double', 'char' or 'cell'."
            )

        if isinstance(target, float):
            key = int(target)
            if param_name == "Line":
                return self.port_line.get(key, -1.0)
            if key in self.line_meta and param_name in self.line_meta[key]:
                return self.line_meta[key][param_name]
            if param_name == "Parent":
                return self.port_parent[key]
            if param_name == "PortNumber":
                return self.port_number[key]

        raise RuntimeError(f"unsupported param: {param_name}")


class FakeInspectEngine:
    """Fake engine for inspect action tests.

    Supports DialogParameters, mask metadata, and per-param value lookup.
    """

    def __init__(
        self,
        values,
        mask_names=None,
        mask_visibilities=None,
        mask_enables=None,
        valid_paths=None,
    ):
        self.values = values
        self.mask_names = mask_names
        self.mask_visibilities = mask_visibilities
        self.mask_enables = mask_enables
        self.valid_paths = set(valid_paths or ["m/b"])

    def get_param(self, block_path, param_name):
        if param_name == "Handle":
            if block_path not in self.valid_paths:
                raise RuntimeError("not found")
            return 1
        if param_name == "DialogParameters":
            return {key: {} for key in self.values.keys()}
        if param_name == "MaskNames":
            if self.mask_names is None:
                raise RuntimeError("not a masked block")
            return self.mask_names
        if param_name == "MaskVisibilities":
            if self.mask_visibilities is None:
                raise RuntimeError("not a masked block")
            return self.mask_visibilities
        if param_name == "MaskEnables":
            if self.mask_enables is None:
                raise RuntimeError("not a masked block")
            return self.mask_enables
        if param_name in self.values:
            return self.values[param_name]
        raise RuntimeError(f"unknown param {param_name}")

    def fieldnames(self, dialog_params):
        return list(dialog_params.keys())


class KeywordNargoutInspectEngine(FakeInspectEngine):
    """Inspect fake whose get_param only works when nargout is passed by keyword."""

    def get_param(self, block_path, param_name, *, nargout):
        return super().get_param(block_path, param_name)


class FakeInspectOutputEngine:
    """Minimal fake engine for inspect output-controls tests.

    Returns two params (A, B) with fixed values, unmasked.
    """

    def get_param(self, block_path, param_name):
        if param_name == "Handle":
            return 1
        if param_name == "DialogParameters":
            return {"B": {}, "A": {}}
        if param_name == "MaskNames":
            raise RuntimeError("not masked")
        if param_name == "MaskVisibilities":
            raise RuntimeError("not masked")
        if param_name == "MaskEnables":
            raise RuntimeError("not masked")
        if param_name in {"A", "B"}:
            return f"value_{param_name}"
        raise RuntimeError("unknown")

    def fieldnames(self, dialog_params):
        return list(dialog_params.keys())


class FakeFindEngine:
    """Fake engine for find action tests.

    Supports find_system with scope-based results, get_param for Handle/BlockType/Type.
    """

    def __init__(self, models, find_results=None, valid_handles=None):
        self.models = models
        self.find_results = find_results or {}
        self.valid_handles = valid_handles or set()

    def find_system(self, *args, **kwargs):
        # Handle get_opened_models() call: find_system("Type", "block_diagram")
        if args == ("Type", "block_diagram"):
            return list(self.models)
        scope = args[0] if args else ""
        return self.find_results.get(scope, [])

    def get_param(self, path, param):
        if param == "Handle":
            if path not in self.valid_handles:
                raise RuntimeError(f"not found: {path}")
            return 1.0
        if param == "BlockType":
            if "SubSystem" in path or "Controller" in path:
                return "SubSystem"
            return "Gain"
        if param == "Type":
            return "block_diagram"
        raise RuntimeError(f"unknown param: {param}")

    def bdroot(self):
        return self.models[0] if self.models else ""


class FakeSetParamEngine:
    """Fake engine for set_param action tests.

    Supports get_param (Handle + keyed params) and set_param with validation.
    """

    def __init__(self, params=None, valid_handles=None):
        self._params = params or {}
        self._valid_handles = valid_handles or set()

    def get_param(self, path, param):
        if param == "Handle":
            if path not in self._valid_handles:
                raise RuntimeError(f"Invalid block path: {path}")
            return 1.0
        key = f"{path}::{param}"
        if key not in self._params:
            raise RuntimeError(f"Parameter '{param}' not found on '{path}'")
        return self._params[key]

    def set_param(self, path, param, value):
        key = f"{path}::{param}"
        if key not in self._params:
            raise RuntimeError(f"Parameter '{param}' not found on '{path}'")
        self._params[key] = value

    def force_param_value(self, path, param, value):
        self._params[f"{path}::{param}"] = value


class FakeCrossSkillEngine:
    """Simulates a MATLAB engine with get_param and set_param.

    Pre-loaded with a single Gain block for read-preview-write-verify cycle tests.
    """

    def __init__(self):
        self._params = {
            "my_model/Gain1::Gain": "1.5",
            "my_model/Gain1::Handle": 1.0,
        }
        self._valid_handles = {"my_model/Gain1"}

    def get_param(self, path, param):
        if param == "Handle":
            if path not in self._valid_handles:
                raise RuntimeError(f"Invalid block path: {path}")
            return 1.0
        if param == "DialogParameters":
            return {"Gain": {}}
        if param == "MaskNames":
            raise RuntimeError("not masked")
        if param == "MaskVisibilities":
            raise RuntimeError("not masked")
        if param == "MaskEnables":
            raise RuntimeError("not masked")
        key = f"{path}::{param}"
        if key not in self._params:
            raise RuntimeError(f"Parameter '{param}' not found on '{path}'")
        return self._params[key]

    def set_param(self, path, param, value):
        key = f"{path}::{param}"
        self._params[key] = value

    def fieldnames(self, dialog_params):
        return list(dialog_params.keys())

    def force_param_value(self, path, param, value):
        self._params[f"{path}::{param}"] = value


class OutputSensitiveEngine:
    def __init__(self):
        self.params = {"m/Gain::Gain": "1.5"}
        self.calls = []
        self.warning_log = []

    def get_param(self, target, param, nargout=1):
        self.calls.append(("get_param", target, param, nargout))
        if param == "Handle":
            return 1.0
        return self.params[f"{target}::{param}"]

    def set_param(self, target, param, value, nargout=1):
        self.calls.append(("set_param", target, param, value, nargout))
        if nargout != 0:
            self.params[f"{target}::{param}"] = value
            raise RuntimeError("Too many output arguments")
        self.params[f"{target}::{param}"] = value

    def find_system(self, *args, nargout=1):
        self.calls.append(("find_system", args, nargout))
        if args != ("Type", "block_diagram"):
            self.warning_log.append("Variant warning")
        return ["m", "m/Gain"]


class WriteThenFailEngine(OutputSensitiveEngine):
    def set_param(self, target, param, value, nargout=1):
        self.calls.append(("set_param", target, param, value, nargout))
        self.params[f"{target}::{param}"] = value
        raise RuntimeError("Persistent write failure")


class VerificationMismatchEngine(OutputSensitiveEngine):
    def get_param(self, target, param, nargout=1):
        value = super().get_param(target, param, nargout=nargout)
        if param == "Gain" and value == "2.0":
            return "1.5"
        return value


class FakeModelEngine:
    """Fake engine for model lifecycle action tests.

    Tracks loaded models in memory. Supports new_system, open_system,
    save_system, and get_param (Handle-only for existence checks).
    """

    def __init__(self, loaded_models=None, filesystem=None, dirty_models=None):
        self._loaded = set(loaded_models or [])
        self._filesystem = set(filesystem or [])
        self._saved = set()
        self._dirty = set(dirty_models or [])

    def new_system(self, name, nargout=1):
        if name in self._loaded:
            raise RuntimeError(f"Model '{name}' is already loaded")
        self._loaded.add(name)
        return name

    def open_system(self, path, nargout=0):
        if path not in self._filesystem and path not in self._loaded:
            raise RuntimeError(f"File '{path}' not found")
        model_name = path.rsplit("/", 1)[-1].replace(".slx", "")
        self._loaded.add(model_name)

    def save_system(self, model, nargout=0):
        if model not in self._loaded:
            raise RuntimeError(f"Model '{model}' is not loaded")
        self._saved.add(model)

    def get_param(self, target, param, nargout=1):
        if param == "Dirty":
            if target not in self._loaded:
                raise RuntimeError(f"Invalid Simulink object name: {target}")
            return "on" if target in self._dirty else "off"
        if param == "Handle":
            model_root = target.split("/")[0]
            if model_root not in self._loaded:
                raise RuntimeError(f"Invalid Simulink object name: {target}")
            return 1.0
        raise RuntimeError(f"Parameter '{param}' not found")

    def close_system(self, model, save_flag=0, nargout=0):
        self._loaded.discard(model)

    def set_param(self, target, param, value, nargout=0):
        if param == "SimulationCommand" and value == "update":
            if target not in self._loaded:
                raise RuntimeError(f"Model '{target}' is not loaded")
            return
        raise RuntimeError(f"Unsupported set_param: {param}={value}")

    @property
    def loaded_models(self):
        return set(self._loaded)

    @property
    def saved_models(self):
        return set(self._saved)


class FakeBlockEngine:
    """Fake engine for block_add action tests.

    Tracks loaded models, existing blocks, and known library sources.
    Supports get_param (Handle) and add_block.
    """

    def __init__(self, loaded_models=None, blocks=None, library_sources=None):
        self._loaded = set(loaded_models or [])
        self._blocks = set(blocks or [])
        self._library_sources = set(library_sources or [])

    def get_param(self, target, param, nargout=1):
        if param == "Handle":
            if target in self._library_sources:
                return 1.0
            if target in self._loaded:
                return 1.0
            if target in self._blocks:
                return 1.0
            raise RuntimeError(f"Invalid Simulink object name: {target}")
        raise RuntimeError(f"Parameter '{param}' not found")

    def add_block(self, source, dest, nargout=0):
        model_root = dest.split("/")[0]
        if model_root not in self._loaded:
            raise RuntimeError(f"Model '{model_root}' is not loaded")
        if dest in self._blocks:
            raise RuntimeError(f"Block '{dest}' already exists")
        self._blocks.add(dest)


class FakeLineEngine(FakeBlockEngine):
    """Fake engine for line_add action tests.

    Extends FakeBlockEngine with line tracking and add_line support.
    """

    def __init__(self, loaded_models=None, blocks=None, library_sources=None):
        super().__init__(loaded_models, blocks, library_sources)
        self._lines = {}  # handle -> (system, src, dst)
        self._dst_ports = set()  # occupied (system, dst) pairs
        self._next_handle = 145.0001

    def add_line(self, system, src, dst, nargout=1):
        if system not in self._loaded:
            raise RuntimeError(f"Model '{system}' is not loaded")
        src_block = src.split("/")[0]
        dst_block = dst.split("/")[0]
        if f"{system}/{src_block}" not in self._blocks:
            raise RuntimeError(f"Block '{src_block}' not found in '{system}'")
        if f"{system}/{dst_block}" not in self._blocks:
            raise RuntimeError(f"Block '{dst_block}' not found in '{system}'")
        dst_key = (system, dst)
        if dst_key in self._dst_ports:
            raise RuntimeError(f"Destination port '{dst}' is already connected")
        handle = self._next_handle
        self._next_handle += 0.0001
        self._lines[handle] = (system, src, dst)
        self._dst_ports.add(dst_key)
        return handle

    def get_param(self, target, param, nargout=1):
        if isinstance(target, float) and param == "Handle":
            if target in self._lines:
                return target
            raise RuntimeError(f"Invalid line handle: {target}")
        return super().get_param(target, param, nargout=nargout)
