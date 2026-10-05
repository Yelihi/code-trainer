import Foundation
import Darwin

let arguments = Array(CommandLine.arguments.dropFirst())
guard arguments.count == 1, ["app", "runner", "forward", "backup", "deploy"].contains(arguments[0]) else {
    fputs("Usage: CodeTrainerService app|runner|forward|backup|deploy\n", stderr)
    exit(64)
}
let home = FileManager.default.homeDirectoryForCurrentUser.path
do {
    // Attribute removable-volume access to this app, then preserve launchd's process identity.
    _ = try Data(contentsOf: URL(fileURLWithPath: "/Volumes/Storage2TB/server/code-trainer/.volume-uuid"))
    let command = arguments[0] == "deploy"
        ? ["/usr/bin/python3", "\(home)/.config/code-trainer/deployment/github_deploy.py", "poll", "\(home)/.config/code-trainer/deployment"]
        : ["/usr/bin/python3", "\(home)/.config/code-trainer/deployment/host.py", arguments[0]]
    let environment = ["HOME=\(home)", "PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
                       "LANG=en_US.UTF-8", "TMPDIR=\(NSTemporaryDirectory())"]
    let argv = command.map { strdup($0) } + [nil]
    let envp = environment.map { strdup($0) } + [nil]
    defer { argv.forEach { free($0) }; envp.forEach { free($0) } }
    guard chdir(home) == 0 else { exit(1) }
    execve(command[0], argv, envp)
    fputs("Code Trainer Service could not start its job.\n", stderr)
    exit(1)
} catch {
    fputs("Code Trainer Service could not access its external storage.\n", stderr)
    exit(1)
}
