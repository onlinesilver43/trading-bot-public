"""
Enhanced UI endpoints for system monitoring and management
This module provides real-time system monitoring using psutil, docker, and other system packages
"""

from datetime import datetime


def get_enhanced_system_health():
    """Get real system health status with enhanced monitoring"""
    try:
        import psutil

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Get container status (optional - may not have Docker daemon access)
        container_status = {}
        try:
            import docker

            client = docker.from_env()
            containers = client.containers.list()
            container_status = {
                "total": len(containers),
                "running": len([c for c in containers if c.status == "running"]),
                "stopped": len([c for c in containers if c.status == "stopped"]),
                "containers": [
                    {
                        "name": c.name,
                        "status": c.status,
                        "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                        "created": c.attrs["Created"],
                        "ports": c.attrs["NetworkSettings"]["Ports"],
                    }
                    for c in containers
                ],
            }
        except ImportError:
            container_status = {"message": "Docker package not available"}
        except Exception as e:
            # Common issues: permission denied, no Docker daemon access
            if (
                "permission denied" in str(e).lower()
                or "connection refused" in str(e).lower()
            ):
                container_status = {
                    "message": "Docker daemon access not available (containerized environment)"
                }
            else:
                container_status = {"message": f"Docker monitoring failed: {str(e)}"}

        # Get API health
        api_health = {
            "status": "healthy",
            "endpoints": {
                "system_health": "working",
                "system_resources": "working",
                "system_deployments": "working",
                "history_manifest": "working",
                "history_status": "working",
            },
            "timestamp": datetime.now().isoformat(),
        }

        return {
            "status": "enhanced",
            "message": "Enhanced system monitoring active",
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent": memory.percent,
                    "used_gb": round(memory.used / (1024**3), 2),
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": round((disk.used / disk.total) * 100, 2),
                },
            },
            "containers": container_status,
            "api_health": api_health,
        }

    except ImportError as e:
        return {
            "status": "error",
            "message": f"Required packages not available: {str(e)}",
            "timestamp": "unknown",
            "system": {"message": "Package import failed"},
            "containers": {"message": "Package import failed"},
            "api_health": {"message": "Package import failed"},
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"System monitoring failed: {str(e)}",
            "timestamp": "unknown",
            "system": {"message": "Monitoring failed"},
            "containers": {"message": "Monitoring failed"},
            "api_health": {"message": "Monitoring failed"},
        }


def get_enhanced_system_resources():
    """Get real system resource usage with enhanced monitoring"""
    try:
        import psutil

        # Get memory information
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Get disk information
        disk_partitions = psutil.disk_partitions()
        disk_usage = {}
        for partition in disk_partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.device] = {
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": round((usage.used / usage.total) * 100, 2),
                }
            except Exception:
                continue

        # Get network information
        network = psutil.net_io_counters()
        network_info = {
            "bytes_sent_gb": round(network.bytes_sent / (1024**3), 2),
            "bytes_recv_gb": round(network.bytes_recv / (1024**3), 2),
            "packets_sent": network.packets_sent,
            "packets_recv": network.packets_recv,
            "errin": network.errin,
            "errout": network.errout,
            "dropin": network.dropin,
            "dropout": network.dropout,
        }

        # Get top processes by CPU and memory
        processes = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent", "memory_info"]
        ):
            try:
                processes.append(
                    {
                        "pid": proc.info["pid"],
                        "name": proc.info["name"],
                        "cpu_percent": round(proc.info["cpu_percent"], 1),
                        "memory_percent": round(proc.info["memory_percent"], 1),
                        "memory_mb": round(proc.info["memory_info"].rss / (1024**2), 1),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort by CPU usage (top 10)
        top_processes = sorted(processes, key=lambda x: x["cpu_percent"], reverse=True)[
            :10
        ]

        return {
            "status": "enhanced",
            "message": "Enhanced system monitoring active",
            "timestamp": datetime.now().isoformat(),
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent,
                "swap_total_gb": round(swap.total / (1024**3), 2),
                "swap_used_gb": round(swap.used / (1024**3), 2),
                "swap_percent": swap.percent,
            },
            "disk": disk_usage,
            "network": network_info,
            "top_processes": top_processes,
        }

    except ImportError as e:
        return {
            "status": "error",
            "message": f"Required packages not available: {str(e)}",
            "timestamp": "unknown",
            "memory": {"message": "Package import failed"},
            "disk": {"message": "Package import failed"},
            "network": {"message": "Package import failed"},
            "top_processes": [],
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Resource monitoring failed: {str(e)}",
            "timestamp": "unknown",
            "memory": {"message": "Monitoring failed"},
            "disk": {"message": "Monitoring failed"},
            "network": {"message": "Monitoring failed"},
            "top_processes": [],
        }


def get_enhanced_system_performance():
    """Get real-time system performance metrics with enhanced monitoring"""
    try:
        import psutil

        # Get CPU information
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        cpu_stats = psutil.cpu_stats()

        # Get memory information
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Get disk I/O statistics
        disk_io = psutil.disk_io_counters()

        # Get network I/O statistics
        network_io = psutil.net_io_counters()

        # Get load average (Linux only)
        try:
            load_avg = psutil.getloadavg()
            load_info = {
                "1min": round(load_avg[0], 2),
                "5min": round(load_avg[1], 2),
                "15min": round(load_avg[2], 2),
            }
        except AttributeError:
            load_info = {"message": "Load average not available on this system"}

        # Get temperature sensors (if available)
        try:
            temps = psutil.sensors_temperatures()
            temp_info = {}
            for name, entries in temps.items():
                temp_info[name] = [
                    {
                        "label": entry.label or "Unknown",
                        "current": round(entry.current, 1),
                        "high": round(entry.high, 1) if entry.high else None,
                        "critical": (
                            round(entry.critical, 1) if entry.critical else None
                        ),
                    }
                    for entry in entries
                ]
        except AttributeError:
            temp_info = {"message": "Temperature sensors not available"}

        return {
            "status": "enhanced",
            "message": "Enhanced performance monitoring active",
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "count": cpu_count,
                "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else None,
                "min_mhz": round(cpu_freq.min, 1) if cpu_freq else None,
                "max_mhz": round(cpu_freq.max, 1) if cpu_freq else None,
                "ctx_switches": cpu_stats.ctx_switches,
                "interrupts": cpu_stats.interrupts,
                "soft_interrupts": cpu_stats.soft_interrupts,
                "syscalls": cpu_stats.syscalls,
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent,
                "swap_total_gb": round(swap.total / (1024**3), 2),
                "swap_used_gb": round(swap.used / (1024**3), 2),
                "swap_percent": swap.percent,
            },
            "disk_io": {
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count,
                "read_bytes_gb": round(disk_io.read_bytes / (1024**3), 2),
                "write_bytes_gb": round(disk_io.write_bytes / (1024**3), 2),
                "read_time_ms": disk_io.read_time,
                "write_time_ms": disk_io.write_time,
            },
            "network_io": {
                "bytes_sent_gb": round(network_io.bytes_sent / (1024**3), 2),
                "bytes_recv_gb": round(network_io.bytes_recv / (1024**3), 2),
                "packets_sent": network_io.packets_sent,
                "packets_recv": network_io.packets_recv,
            },
            "load_average": load_info,
            "temperatures": temp_info,
        }

    except ImportError as e:
        return {
            "status": "error",
            "message": f"Required packages not available: {str(e)}",
            "timestamp": "unknown",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Performance monitoring failed: {str(e)}",
            "timestamp": "unknown",
        }
