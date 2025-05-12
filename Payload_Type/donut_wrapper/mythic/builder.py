import os
from pathlib import PurePath
from distutils.dir_util import copy_tree
import asyncio
import tempfile

from mythic_container.PayloadBuilder import (
    BuildParameter,
    BuildParameterType,
    BuildResponse,
    BuildStatus,
    BuildStep,
    PayloadType,
)

from mythic_container.MythicCommandBase import (
    SupportedOS
)

from mythic_container.MythicRPC import (
    SendMythicRPCPayloadUpdatebuildStep,
    MythicRPCPayloadUpdateBuildStepMessage,
)


class DonutWrapper(PayloadType):
    name = "donut_wrapper"
    file_extension = "exe"
    author = "Lavender Millstone"
    note = "Wrapper to turn .NET, VBScript, JScript, EXE, and DLL files into Position-Independent Code (PIC) using Donut."
    support_os = [SupportedOS.Windows, SupportedOS.Linux]

    wrapper = True
    wrapped_payloads = []

    supports_dynamic_loading = False
    c2_profiles = []

    agent_path = PurePath(".") / "donut_wrapper"
    agent_icon_path = agent_path / "mythic" / "donut.svg"
    agent_code_path = agent_path / "agent_code"

    build_steps = [
        BuildStep(step_name = "Gathering Files", step_description = "Copy files to temporary location"),
        BuildStep(step_name = "Building", step_description = "Build PIC"),
    ]

    build_parameters = [
        BuildParameter(
            name = "architecture",
            parameter_type = BuildParameterType.ChooseOne,
            description = "Select the Loader's Architecture. 1 = x86, 2 = amd64, 3 = x86+amd64 (Default).",
            choices = ["1", "2", "3"],
            default_value = "3"
        ),

        BuildParameter(
            name = "bypass",
            parameter_type = BuildParameterType.ChooseOne,
            description = "Behaviour for bypassing AMSI/WLDP. 1 = None, 2 = Abort On Fail, 3 = Continue On Fail (Default).",
            choices = ["1", "2", "3"],
            default_value = "3"
        ),

        BuildParameter(
            name = "headers",
            parameter_type = BuildParameterType.ChooseOne,
            description = "Preserve PE Headers. 1 = Overwrite (Default), 2 = Keep All.",
            choices = ["1", "2"],
            default_value = "1"
        ),

        BuildParameter(
            name = "class",
            parameter_type = BuildParameterType.String,
            description = "Optional class name. (required for .NET DLL) Can also include namespace: e.g namespace.class.",
            default_value = ""
        ),

        BuildParameter(
            name = "appdomain",
            parameter_type = BuildParameterType.String,
            description = "AppDomain name to create for .NET. If entropy is enabled, one will be generated randomly.",
            default_value = ""
        ),

        BuildParameter(
            name = "entropy",
            parameter_type = BuildParameterType.ChooseOne,
            description = "Entropy level. 1 = None, 2 = Generate Random Names, 3 = Generate Random Names + Use Symmetric Encryption (Default).",
            choices = ["1", "2", "3"],
            default_value = "3"
        ),

        BuildParameter(
            name = "format",
            parameter_type = BuildParameterType.ChooseOne,
            description = "The output format of loader saved to file. 1 = Binary (Default), 2 = Base64, 3 = C, 4 = Ruby, 5 = Python, 6 = PowerShell, 7 = C#, 8 = Hexadecimal",
            choices = ["1", "2", "3", "4", "5", "6", "7", "8"],
            default_value = "1"
        ),

        BuildParameter(
            name = "method",
            parameter_type = BuildParameterType.String,
            description = "Optional method or function for DLL. (a method is required for .NET DLL).",
            default_value = ""
        ),

        BuildParameter(
            name = "module",
            parameter_type = BuildParameterType.String,
            description = "Module name for HTTP staging. If entropy is enabled, one is generated randomly.",
            default_value = ""
        ),

        BuildParameter(
            name = "parameters",
            parameter_type = BuildParameterType.String,
            description = "Optional parameters/command line inside quotations for DLL method/function or EXE.",
            default_value = ""
        ),

        BuildParameter(
            name = "runtime",
            parameter_type = BuildParameterType.String,
            description = "CLR runtime version. MetaHeader used by default or v4.0.30319 if none available.",
            default_value = ""
        ),

        BuildParameter(
            name = "server",
            parameter_type = BuildParameterType.String,
            description = "URL for the HTTP server that will host a Donut module. Credentials may be provided in the following format: https://username:password@192.168.0.1/",
            default_value = ""
        ),

        BuildParameter(
            name = "exit",
            parameter_type = BuildParameterType.ChooseOne,
            description = "Determines how the loader should exit. 1 = Exit Thread (default), 2 = Exit Process, 3 = Do not exit or cleanup and block indefinitely.",
            choices = ["1", "2", "3"],
            default_value = "1"
        ),

        BuildParameter(
            name = "engine",
            parameter_type = BuildParameterType.ChooseOne,
            description = "Pack/Compress the input file. 1 = None, 2 = aPLib, 3 = LZNT1, 4 = Xpress, 5 = Xpress Huffman. Currently, the last three are only supported on Windows.",
            choices = ["1", "2", "3", "4", "5"],
            default_value = "1"
        ),

        BuildParameter(
            name = "runasthread",
            parameter_type = BuildParameterType.Boolean,
            description = "Run the entrypoint of an unmanaged/native EXE as a thread and wait for thread to end.",
            default_value = False
        ),
    ]

    async def build(self) -> BuildResponse:
        response = BuildResponse(status = BuildStatus.Error)
        output = ""
        try:
            agent_build_path = tempfile.TemporaryDirectory(suffix = self.uuid).name
            copy_tree(str(self.agent_code_path), agent_build_path)

            working_path = f"{PurePath(agent_build_path)}/donut_v1.1/output/loader.bin"
            output_path = f"{PurePath(agent_build_path)}/donut_v1.1/output/donut.bin"
            output_path = str(output_path)

            with open(str(working_path), "wb") as file:
                file.write(self.wrapped_payload)
            await SendMythicRPCPayloadUpdatebuildStep(MythicRPCPayloadUpdateBuildStepMessage(
                PayloadUUID = self.uuid,
                StepName = "Gathering Files",
                StepStdout = "Found necessary files for payload",
                StepSuccess = True
            ))

            command = f"cd {agent_build_path}/donut_v1.1/; chmod +x donut; ./donut"
            command += f" -a {self.get_parameter('architecture')}"
            command += f" -b {self.get_parameter('bypass')}"
            command += f" -k {self.get_parameter('headers')}"
            command += f" -c {self.get_parameter('class')}"
            command += f" -d {self.get_parameter('appdomain')}"
            command += f" -e {self.get_parameter('entropy')}"
            command += f" -f {self.get_parameter('format')}"
            command += f" -m {self.get_parameter('method')}"
            command += f" -n {self.get_parameter('module')}"
            command += f" -p {self.get_parameter('parameters')}"
            command += f" -r {self.get_parameter('runtime')}"
            command += f" -s {self.get_parameter('server')}"
            command += f" -x {self.get_parameter('exit')}"
            command += f" -z {self.get_parameter('engine')}"
            command += " -t" if self.get_parameter('runasthread') else " "
            command += f" -o {output_path}"

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=agent_build_path
            )

            stdout, stderr = await process.communicate()

            if stdout:
                output += f"[stdout]\n{stdout.decode()}"
            if stderr:
                output += f"[stderr]\n{stderr.decode()}"

            if os.path.exists(output_path):
                response.payload = open(output_path, "rb").read()
                response.status = BuildStatus.Success
                response.build_message = "Shellcode Generated!"
            else:
                response.payload = b""
                response.build_stderr = output + "\n" + output_path

        except Exception as e:
            raise Exception(str(e) + "\n" + output)

        return response
