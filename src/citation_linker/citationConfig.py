import  argparse
from    importlib.resources         import files
from    citation_linker.configPaths import  resolve_config_path, resolve_dir_paths, show_active_paths


# za spreminajanje poti iz kjer se bere .config in ali input output dir
def args_parser():
    parser = argparse.ArgumentParser(description="poti/path do config in ostalo")
    parser.add_argument("--config", help="path do .config datoteke npr ./.config")
    parser.add_argument("--input", help="path do input mape")
    parser.add_argument("--output", help="path do output mape")
    parser.add_argument("--list", action="store_true", help="pokazi vse poti")

    args = parser.parse_args()
    return args

def main():
    args = args_parser()
    dirs = {
            "input": args.input,
            "output": args.output
            }

    if args.config:
        config_path = resolve_config_path(args.config)
        print("config_path spremenjen v: ", str(config_path))
        print("----")

    if args.input or args.output:
        io_paths = resolve_dir_paths(dirs)
        for path, value in io_paths.items():
            print(f"{path} dir: {value}")
            print("----")

    if args.list:
        all_paths = show_active_paths()
        for path, value in all_paths.items():
            if path == "config":
                print(f"{path} {'path location file:':<25} {value}")
                print(f"{path} {'location:':<25} {value.read_text().strip()}")
                print("----")

            else:
                print(f"{path:<5} {'dir:':<25} {value}")
                print(f"{path} {'location:':<25} {value.read_text().strip()}")
                print("----")




if __name__ == "__main__":
    main()
