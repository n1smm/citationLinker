import  argparse
from    citation_linker.configPaths         import  resolve_config_path, resolve_dir_paths, show_active_paths


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

    config_path = resolve_config_path(args.config)
    io_paths = resolve_dir_paths(dirs)
    all_paths = show_active_paths()

    print("config_path spremenjen v: ", config_path)
    print("io paths: ", io_paths)

    print("all_paths: ", all_paths)


if __name__ == "__main__":
    main()
