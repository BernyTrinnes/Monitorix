from collections import deque
from pathlib import Path
from re import sub as re_sub
from sys import argv as sys_argv, exit as sys_exit


def _execute_checks() -> None:
    # Check the supplied CLI argument(s)
    if len(sys_argv) <= 1:
        sys_exit("The directory containing the Monitorix config file must be supplied.")
    
    # Check the Monitorix configuration file
    global _conf_file_orig
    _conf_file_orig = Path(sys_argv[1], "monitorix.conf")
    if not _conf_file_orig.is_file():
        sys_exit(f"'{_conf_file_orig}' is not a valid file.")


def _read_graphs() -> None:
    # Read the graphs from the Monitorix configuration file
    monitorix_graphs = []
    with _conf_file_orig.open("r") as conf_file:
        process_graphs = False
        
        for line in conf_file:
            if "<graph_enable>" in line:
                process_graphs = True
                continue
            if "</graph_enable>" in line:
                break
            
            if process_graphs:
                monitorix_graphs.append(line.split("=")[0].strip())
    
    if not monitorix_graphs:
        sys_exit("Could not find the Monitorix graphs configurations.")
    
    # These configurations can also be extracted
    _monitorix_graphs.extend(["httpd_builtin", "piwik_tracking"])
    _monitorix_graphs.extend(monitorix_graphs)
    _monitorix_graphs.extend(["traffacct", "multihost", "emailreports"])


def _extract_graph_configuration() -> None:
    print("Adapting the configuration file to the Debian configuration structure.")
    
    for (index, monitorix_graph) in enumerate(_monitorix_graphs, 1):
        print(f"   - Processing graph '{monitorix_graph}' ...")
        start_tag = f"<{monitorix_graph}>"
        end_tag = f"</{monitorix_graph}>"
        
        # Graph configuration file
        conf_file_name = f"{index:02d}-{monitorix_graph}.conf".replace("_", "-")
        conf_file_graph_ = Path(sys_argv[1], "conf.d", conf_file_name)
        # Work on a copy of the main configuration file
        conf_file_tmp_: Path = _conf_file_orig.replace(_conf_file_orig.with_suffix(".tmp"))
        
        # Iterate over the temp file and move every line, not being a config of the current graph, to the original file
        with conf_file_tmp_.open("r") as conf_file_tmp:
            with _conf_file_orig.open("w") as conf_file_orig:
                with conf_file_graph_.open("w") as conf_file_graph:
                    process_graph_configuration = False
                    lines_queue: deque[str] = deque(maxlen=_MAX_QUEUE_LENGTH)
                    
                    for line in conf_file_tmp:
                        # Buffer some line until the may queue length has been reached
                        lines_queue.append(line)
                        if len(lines_queue) < _MAX_QUEUE_LENGTH and not process_graph_configuration:
                            continue
                        
                        # Check if the current line is a starting or ending tag for the current graph
                        if start_tag in line:
                            process_graph_configuration = True
                            
                            # Copy the lines to the graph configuration file, if they are comments, or the start tag
                            for line_queue in lines_queue:
                                if line_queue.startswith("#") or start_tag in line_queue:
                                    conf_file_graph.write(line_queue)
                                else:
                                    conf_file_orig.write(line_queue)
                            lines_queue.clear()
                            continue
                        
                        if end_tag in line:
                            process_graph_configuration = False
                            
                            # Copy the lines to the graph configuration file
                            for line_queue in reversed(lines_queue):
                                conf_file_graph.write(line_queue)
                            lines_queue.clear()
                            conf_file_graph.write("\n")
                            continue
                        
                        # Copy lines not pertaining to the graph configuration
                        if not process_graph_configuration and not end_tag in line:
                            conf_file_orig.write(lines_queue.popleft())
                            continue
                        
                        # Copy the lines to the graph configuration file
                        for line_queue in lines_queue:
                            conf_file_graph.write(line_queue)
                        lines_queue.clear()
                    
                    # Write the remaining items in the queue to the main configuration file
                    if len(lines_queue) > 0:
                        for line_queue in lines_queue:
                            conf_file_orig.write(line_queue)
        
        # Remove the temporary file
        conf_file_tmp_.unlink(True)


def _remove_blank_lines() -> None:
    # Rename the file
    conf_file_tmp_: Path = _conf_file_orig.replace(_conf_file_orig.with_suffix(".tmp"))
    
    with conf_file_tmp_.open("r") as conf_file_tmp:
        with _conf_file_orig.open("w") as conf_file_orig:
            content = conf_file_tmp.read()
            cleaned_content = re_sub(r"\n\s*\n", "\n\n", content)
            conf_file_orig.write(cleaned_content)
            conf_file_orig.write("\n")
    
    # Remove the temporary file
    conf_file_tmp_.unlink(True)


# Global variables and constants
_conf_file_orig: Path | None = None
_monitorix_graphs: list[str] = []
_MAX_QUEUE_LENGTH = 3

# Main execution
_execute_checks()
_read_graphs()
_extract_graph_configuration()
_remove_blank_lines()
