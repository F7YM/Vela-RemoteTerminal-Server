import sys
import os
import ast
import re
import asyncio
import zipfile
from typing import List, Set, Dict, Optional
import httpx

# 获取所有Python标准库模块名
def get_stdlib_modules():
    """获取Python标准库模块列表"""
    stdlib_modules = set()
    stdlib_modules.update(sys.builtin_module_names)
    
    stdlib_path = os.path.dirname(os.__file__)
    for root, dirs, files in os.walk(stdlib_path):
        for file in files:
            if file.endswith('.py'):
                module_name = file[:-3]
                if module_name not in ['__init__', '__main__']:
                    stdlib_modules.add(module_name)
            elif file.endswith('.pyc'):
                module_name = file[:-4]
                if module_name not in ['__init__', '__main__']:
                    stdlib_modules.add(module_name)
        for dir_name in dirs:
            if dir_name not in ['__pycache__', 'site-packages']:
                stdlib_modules.add(dir_name)
    return stdlib_modules

STDLIB_MODULES = get_stdlib_modules()

def analyze_project_imports(
    project_dir: str,
    ignore_modules: Optional[List[str]] = None,
    ignore_stdlib: bool = True
) -> Dict[str, Set[str]]:
    """分析项目导入，返回分类字典"""
    if not os.path.isdir(project_dir):
        raise ValueError(f"目录不存在: {project_dir}")
    
    ignore_modules = set(ignore_modules or [])
    project_dir = os.path.abspath(project_dir)
    
    def is_ignored_module(module_name: str) -> bool:
        if not module_name:
            return True
        if module_name in ignore_modules:
            return True
        for ignore in ignore_modules:
            if module_name.startswith(ignore + '.'):
                return True
        if ignore_stdlib and is_stdlib_module(module_name):
            return True
        return False
    
    def is_stdlib_module(module_name: str) -> bool:
        if module_name in STDLIB_MODULES:
            return True
        for stdlib in STDLIB_MODULES:
            if module_name.startswith(stdlib + '.'):
                return True
        return False
    
    def is_local_module(module_name: str, local_modules: Set[str]) -> bool:
        if not module_name or module_name.startswith('.'):
            return True
        for local in local_modules:
            if module_name == local or module_name.startswith(local + '.'):
                return True
        return False
    
    def scan_local_modules(target_dir: str) -> Set[str]:
        local_modules = set()
        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env']]
            for file in files:
                if file.endswith('.py'):
                    rel_path = os.path.relpath(os.path.join(root, file), target_dir)
                    module_name = rel_path[:-3].replace(os.sep, '.')
                    if file != '__init__.py':
                        local_modules.add(module_name)
                    else:
                        parent = os.path.dirname(rel_path).replace(os.sep, '.')
                        if parent:
                            local_modules.add(parent)
        return local_modules
    
    def classify_import(module: str, imports: Dict, local_modules: Set[str]):
        if is_local_module(module, local_modules):
            imports['local'].append(module)
        elif is_stdlib_module(module):
            imports['ignored'].append(module)
        else:
            try:
                __import__(module)
                imports['external'].append(module)
            except ImportError:
                imports['unknown'].append(module)
    
    def analyze_file_imports(file_path: str, local_modules: Set[str]) -> Dict:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
        except Exception:
            return {'local': [], 'external': [], 'unknown': [], 'ignored': []}
        
        imports = {'local': [], 'external': [], 'unknown': [], 'ignored': []}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if is_ignored_module(module):
                        imports['ignored'].append(module)
                    else:
                        classify_import(module, imports, local_modules)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.module.startswith('.'):
                        imports['local'].append(node.module)
                    else:
                        module = node.module.split('.')[0]
                        if is_ignored_module(module):
                            imports['ignored'].append(module)
                        else:
                            classify_import(module, imports, local_modules)
        return imports
    
    local_modules = scan_local_modules(project_dir)
    all_imports = {'local': set(), 'external': set(), 'unknown': set(), 'ignored': set()}
    
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env']]
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                imports = analyze_file_imports(file_path, local_modules)
                all_imports['local'].update(imports['local'])
                all_imports['external'].update(imports['external'])
                all_imports['unknown'].update(imports['unknown'])
                all_imports['ignored'].update(imports['ignored'])
    
    return all_imports

def get_whl_from_tuna(
    package_name: str,
    platform: str = None,
    python_version: Optional[str] = None,
    version: Optional[str] = None,
    verbose: bool = False
) -> Optional[Dict[str, str]]:
    """从清华镜像获取whl信息（httpx）"""
    import platform as plat
    
    if platform is None:
        system = plat.system().lower()
        machine = plat.machine().lower()
        if system == 'windows':
            platform = 'win_amd64' if machine in ['amd64', 'x86_64'] else 'win32'
        elif system == 'linux':
            platform = 'manylinux_x86_64'
        elif system == 'darwin':
            platform = 'macosx_11_0_arm64' if machine == 'arm64' else 'macosx_10_9_x86_64'
        else:
            platform = 'any'
    
    if python_version is None:
        py_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    else:
        py_tag = f"cp{python_version.replace('.', '')}"
    
    url = f"https://pypi.tuna.tsinghua.edu.cn/simple/{package_name}/"
    try:
        if verbose:
            print(f"  请求: {url}")
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html_content = resp.text
        if verbose:
            print(f"  状态码: {resp.status_code}, 响应大小: {len(html_content)} 字符")
    except Exception as e:
        if verbose:
            print(f"  请求失败: {e}")
        return None
    
    # 提取whl链接
    whl_pattern = r'href=[\'"]([^\'"]+\.whl)[\'"]'
    whl_links = re.findall(whl_pattern, html_content, re.IGNORECASE)
    if not whl_links:
        whl_pattern = r'([^\s\'"]+\.whl)'
        whl_links = re.findall(whl_pattern, html_content, re.IGNORECASE)
    
    if verbose:
        print(f"  找到 {len(whl_links)} 个 whl 文件")
    
    if not whl_links:
        # 尝试源码包
        src_pattern = r'href=[\'"]([^\'"]+\.(?:tar\.gz|zip))[\'"]'
        src_links = re.findall(src_pattern, html_content, re.IGNORECASE)
        if src_links:
            src_path = src_links[0]
            if src_path.startswith('../../'):
                src_path = src_path[5:]
            elif src_path.startswith('../'):
                src_path = src_path[3:]
            return {
                'filename': src_path.split('/')[-1].split('#')[0],
                'url': f"https://pypi.tuna.tsinghua.edu.cn/packages/{src_path}",
                'version': 'latest (source)'
            }
        return None
    
    # 打分匹配
    best = None
    best_score = -1
    current_py_num = int(py_tag[2:])
    
    for whl_path in whl_links:
        clean_path = whl_path
        if clean_path.startswith('../../'):
            clean_path = clean_path[5:]
        elif clean_path.startswith('../'):
            clean_path = clean_path[3:]
        
        filename = clean_path.split('/')[-1].split('#')[0]
        if not filename.lower().startswith(package_name.lower()):
            continue
        
        score = 0
        if version and version in filename:
            score += 100
        if platform != 'any' and platform in filename:
            score += 50
        elif "any" in filename:
            score += 10
        
        cp_matches = re.findall(r'cp(\d{2,3})', filename)
        if cp_matches:
            pkg_py_num = int(cp_matches[0])
            if pkg_py_num <= current_py_num:
                score += 30
                if pkg_py_num == current_py_num:
                    score += 20
            else:
                score -= 50
        else:
            score += 20
        
        if score > best_score:
            best_score = score
            best = clean_path
    
    if best:
        filename = best.split('/')[-1].split('#')[0]
        ver_match = re.search(rf'{package_name}-([\d.]+)', filename, re.IGNORECASE)
        ver = ver_match.group(1) if ver_match else "unknown"
        
        # 修复URL：best 已经是 packages/xxx 格式
        url = f"https://pypi.tuna.tsinghua.edu.cn/{best}"
        url = re.sub(r'/+', '/', url)
        url = url.replace('https:/', 'https://')
        
        return {
            'filename': filename,
            'url': url,
            'version': ver
        }
    
    return None

async def download_whl_async(
    whl_info: Dict[str, str],
    target_dir: str,
    client: httpx.AsyncClient,
    skip_existing: bool = True
) -> bool:
    if not whl_info:
        return False
    os.makedirs(target_dir, exist_ok=True)
    filename = whl_info['filename']
    filepath = os.path.join(target_dir, filename)
    if skip_existing and os.path.exists(filepath):
        print(f"  跳过: {filename} (已存在)")
        return True
    url = whl_info['url']
    try:
        print(f"  下载: {filename}")
        async with client.stream('GET', url, timeout=60.0) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            with open(filepath, 'wb') as f:
                downloaded = 0
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"\r  进度: {progress:.1f}%", end='')
        print(f"\r  完成: {filename}")
        return True
    except Exception as e:
        print(f"\r  下载失败: {e}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return False

async def download_all_whls_async(
    external_list: List[str],
    target_dir: str,
    platforms: List[str] = None,
) -> Dict[str, bool]:
    if platforms is None:
        platforms = ['any', 'manylinux_x86_64', 'win_amd64']
    
    results = {}
    total = len(external_list)
    
    # 先扫描lib目录，获取已下载的包名集合
    existing_packages = set()
    if os.path.exists(target_dir):
        for filename in os.listdir(target_dir):
            if filename.endswith('.whl'):
                # 用 - 分割，取第一个部分作为包名
                parts = filename.split('-')
                if parts:
                    pkg_name = parts[0].replace('_', '-')
                    existing_packages.add(pkg_name)
    
    limits = httpx.Limits(max_keepalive_connections=20, max_connections=20)
    async with httpx.AsyncClient(timeout=30.0, limits=limits) as client:
        for i, module in enumerate(external_list, 1):
            print(f"[{i}/{total}] 处理 {module}")
            
            # 检查是否已存在
            if module in existing_packages:
                print(f"  跳过: {module} (已存在)")
                results[module] = True
                continue
            
            module_success = False
            for platform in platforms:
                print(f"  尝试平台: {platform}")
                whl_info = get_whl_from_tuna(module, platform=platform, verbose=False)
                if whl_info:
                    success = await download_whl_async(whl_info, target_dir, client, skip_existing=True)
                    if success:
                        module_success = True
                        break
                else:
                    print(f"  平台 {platform} 没有找到匹配的whl")
            
            results[module] = module_success
            if not module_success:
                print(f"  警告: {module} 没有找到可用的whl")
    
    return results

def parse_gitignore(gitignore_path: str) -> List[str]:
    """
    解析.gitignore文件，返回忽略模式列表
    
    Args:
        gitignore_path: .gitignore文件路径
    
    Returns:
        忽略模式列表
    """
    patterns = []
    if not os.path.exists(gitignore_path):
        return patterns
    
    try:
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                # 移除末尾的注释
                if '#' in line:
                    line = line.split('#')[0].strip()
                # 跳过空行
                if not line:
                    continue
                # 移除开头的 ! (negation pattern)，暂不处理
                if line.startswith('!'):
                    continue
                # 移除开头的 /，统一处理
                if line.startswith('/'):
                    line = line[1:]
                # 移除结尾的 / (目录)
                if line.endswith('/'):
                    line = line[:-1]
                patterns.append(line)
    except Exception:
        pass
    
    return patterns

def should_ignore_by_pattern(
    path: str,
    gitignore_patterns: List[str],
    is_dir: bool = False
) -> bool:
    """
    检查路径是否匹配gitignore模式
    
    Args:
        path: 相对路径
        gitignore_patterns: gitignore模式列表
        is_dir: 是否是目录
    
    Returns:
        是否应该忽略
    """
    for pattern in gitignore_patterns:
        # 精确匹配
        if path == pattern:
            return True
        # 路径中包含模式
        if f"/{pattern}/" in f"/{path}/":
            return True
        # 通配符匹配 (简单处理 * )
        if '*' in pattern:
            # 将通配符转换为正则表达式
            regex_pattern = pattern.replace('.', '\\.').replace('*', '[^/]*')
            if re.search(regex_pattern, path):
                return True
        # 目录结尾匹配
        if is_dir and path.endswith(f"/{pattern}"):
            return True
        # 目录匹配
        if path.startswith(pattern + '/'):
            return True
    
    return False

def zip_folder(
    source_dir: str,
    output_path: str = None,
    extra_ignore: List[str] = None
) -> str:
    """
    打包文件夹为zip文件，自动识别.gitignore
    
    Args:
        source_dir: 要打包的源文件夹路径
        output_path: 输出zip文件路径，None则自动生成
        extra_ignore: 额外的忽略模式列表
    
    Returns:
        生成的zip文件路径
    """
    source_dir = os.path.abspath(source_dir)
    if not os.path.isdir(source_dir):
        raise ValueError(f"目录不存在: {source_dir}")
    
    # 读取.gitignore
    gitignore_path = os.path.join(source_dir, '.gitignore')
    gitignore_patterns = parse_gitignore(gitignore_path)
    
    # 默认忽略模式
    default_ignore = ['__pycache__', '.git', '.venv', 'venv', 'env', '.DS_Store', '.idea', '.vscode']
    if extra_ignore:
        default_ignore.extend(extra_ignore)
    
    # 合并所有忽略模式
    all_ignore = {
        'patterns': default_ignore.copy(),
        'gitignore': gitignore_patterns
    }
    
    def should_ignore_file(file_path: str, is_dir: bool = False) -> bool:
        """检查是否应该忽略"""
        name = os.path.basename(file_path)
        rel_path = os.path.relpath(file_path, source_dir)
        
        # 检查默认忽略模式
        for pattern in default_ignore:
            if name == pattern or pattern in rel_path.split(os.sep):
                return True
        
        # 检查.gitignore模式
        if gitignore_patterns:
            if should_ignore_by_pattern(rel_path, gitignore_patterns, is_dir):
                return True
        
        return False
    
    # 生成输出路径
    if output_path is None:
        dir_name = os.path.basename(source_dir)
        parent_dir = os.path.dirname(source_dir)
        output_path = os.path.join(parent_dir, f"{dir_name}.zip")
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    if gitignore_patterns:
        print(f"从.gitignore读取: {len(gitignore_patterns)} 个模式")
    else:
        print("未找到.gitignore文件")
    
    file_count = 0
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # 过滤要忽略的目录
            filtered_dirs = []
            for d in dirs:
                dir_path = os.path.join(root, d)
                if not should_ignore_file(dir_path, is_dir=True):
                    filtered_dirs.append(d)
            dirs[:] = filtered_dirs
            
            for file in files:
                file_path = os.path.join(root, file)
                if should_ignore_file(file_path, is_dir=False):
                    continue
                
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)
                file_count += 1
                
                if file_count % 50 == 0:
                    print(f"  已打包: {file_count} 个文件")
    
    print(f"打包完成: {file_count} 个文件")
    return output_path

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        project_dir = sys.argv[1]
        
        print("分析项目导入")
        
        ignore_list = []
        try:
            with open("requirements.txt", "r", encoding="utf-8") as f:
                ignore_list = [line.strip().split('>')[0].split('=')[0].split('<')[0].split('~')[0] 
                              for line in f if line.strip() and not line.startswith('#')]
            ignore_list.append('hydroApp')
        except FileNotFoundError:
            print("警告: requirements.txt 不存在")
        
        result = analyze_project_imports(project_dir, ignore_list, ignore_stdlib=True)
        print("外部库: ", end="")
        external_list = sorted(result['external'])
        if external_list:
            for i, module in enumerate(external_list):
                if i == len(external_list) - 1:
                    print(f"{module}")
                else:
                    print(f"{module}", end=", ")
            
            lib_dir = os.path.join(project_dir, 'lib')
            print(f"创建lib目录: {lib_dir}")
            os.makedirs(lib_dir, exist_ok=True)
            
            print("下载whl文件到lib目录")
            print("目标平台: manylinux_x86_64, win_amd64")
            
            download_results = asyncio.run(
                download_all_whls_async(
                    external_list, 
                    lib_dir,
                    platforms=['any', 'manylinux_x86_64', 'win_amd64']
                )
            )
            
            for module, success in download_results.items():
                if not success:
                    print(f"  Warning: {module} 下载失败或未找到whl")
        else:
            print("无外部库")
        
        print("打包HydroApp")
        zip_path = zip_folder(project_dir)
        print(f"打包完成: {zip_path}")
    else:
        print("用法: python pack_hydroapp.py <项目目录>")
        sys.exit(1)