@echo off


{% macro start_section(name, silent=False) %}
echo {{metadata(section=name)}}
{% if not silent %}
echo [{{name.title().replace('_',' ')}}]
{% endif %}
set "CURRENT_SECTION_TAG={{name}}"
{% endmacro %}
{% macro set_error(fail_type='error') -%}
set "BINSTAR_BUILD_RESULT={{fail_type}}" & goto:eof
{%- endmacro %}

{%macro check_result() -%}
if not "%BINSTAR_BUILD_RESULT%" == "" (
    if not "%BINSTAR_BUILD_RESULT%" == "success" (
        echo The build ended in %BINSTAR_BUILD_RESULT% in section %CURRENT_SECTION_TAG%
    )
    goto:eof
)
{%- endmacro %}

{{ start_section('build_env_exports', silent=True) }}
set "PYTHONUNBUFFERED=TRUE"
{% for key, value in exports -%}
set "{{key}}={{value}}"
{% endfor %}

call:parse_options %*
call:main
goto:eof

:: #######################################################
:: Functions
:: #######################################################

:parse_options
  {{ start_section('parse_options', silent=True) }}

  :parse_options_loop
    IF NOT "%1"=="" (

        IF "%1"=="--git-oauth-token" (
            SHIFT
            set GIT_OAUTH_TOKEN=%2
            SHIFT
            goto:parse_options_loop
        )

        IF "%1"=="--build-tarball" (
            SHIFT
            set BUILD_TARBALL=%2
            SHIFT
            goto:parse_options_loop
        )

        IF "%1"=="--api-token" (
            SHIFT
            set "BINSTAR_API_TOKEN=%2"
            SHIFT
            goto:parse_options_loop
        )

        echo "Unknown option %1"
        exit {{EXIT_CODE_ERROR}}

    )


goto:eof

:main

    set BINSTAR_BUILD_RESULT=


    {% if ignore_setup_build %}
    echo [ignore setup_build]
    {% else %}
    call:setup_build;
    {% endif %}


    if not "%BINSTAR_BUILD_RESULT%" == "" (
        echo Internal binstar build error: Could not set up initial build state
        exit {{EXIT_CODE_ERROR}}
    )

    {% if ignore_fetch_build_source %}
    echo [ignore fetch_build_source]
    {% else %}
    call:fetch_build_source
    {% endif %}


    if not "%BINSTAR_BUILD_RESULT%" == "" (
        echo %BINSTAR_BUILD_RESULT%: Could not fetch build sources
        exit {{EXIT_CODE_ERROR}}
    )

    call:binstar_build
    call:binstar_post_build

    call:upload_build_targets

    echo Exit BINSTAR_BUILD_RESULT=%BINSTAR_BUILD_RESULT%

    if "%BINSTAR_BUILD_RESULT%" == "success" (
        echo {{metadata(binstar_build_result='success')}}
        exit {{EXIT_CODE_OK}}
    )
    if "%BINSTAR_BUILD_RESULT%" == "error" (
        echo {{metadata(binstar_build_result='error')}}
        exit {{EXIT_CODE_ERROR}}
    )

    if "%BINSTAR_BUILD_RESULT%" == "failure" (
        echo {{metadata(binstar_build_result='failure')}}
        exit {{EXIT_CODE_FAILED}}
    )

    exit {{EXIT_CODE_ERROR}}


goto:eof

:: #######################################################

:fetch_build_source

    set "SOURCE_DIR=%WORKING_DIR%\source"

    @echo off

    {{ start_section('fetch_build_source') }}

    Rmdir /s /q "%SOURCE_DIR%"

    {% if git_info %}

        set "GIT_REPO={{git_info['full_name']}}"
        set "GIT_BRANCH={{git_info['branch']}}"
        set "GIT_COMMIT={{git_info['commit']}}"

        echo git clone --recursive --depth=50 --branch=%GIT_BRANCH% https://github.com/%GIT_REPO%.git "%SOURCE_DIR%"

        if "%GIT_OAUTH_TOKEN%" == "" (
            git clone --recursive --depth=50 --branch="%GIT_BRANCH%" "https://github.com/%GIT_REPO%.git" "%SOURCE_DIR%"  || ( {{set_error()}} )
        )
        if NOT  "%GIT_OAUTH_TOKEN%" == "" (
            git clone --recursive --depth=50 --branch="%GIT_BRANCH%" "https://%GIT_OAUTH_TOKEN%:x-oauth-basic@github.com/%GIT_REPO%.git" "%SOURCE_DIR%"  || ( {{set_error()}} )
        )

        cd "%SOURCE_DIR%"

        echo "git checkout --quiet %GIT_COMMIT%"
        git checkout --quiet "%GIT_COMMIT%"  || ( {{set_error()}} )

        :: Remove the oath token or (this would be a security violation)
        git remote rm origin  || ( {{set_error()}} )

    {% else %}

        Mkdir "%SOURCE_DIR%"
        cd "%SOURCE_DIR%"
        echo ls  -al %BUILD_TARBALL%
        ls  %BUILD_TARBALL%
        echo "Extracting Package"
        echo tar jxf %BUILD_TARBALL%

        :: tar jxf "%BUILD_TARBALL%" || {{set_error()}}
        python -c "import tarfile; tarfile.open(r'%BUILD_TARBALL%', 'r|bz2').extractall()" || ( {{set_error()}} )
    {% endif %}

    {% if sub_dir %}

    echo Chaning into sub directory of git repository
    echo cd {{sub_dir}}
    cd "{{sub_dir}}" || ( {{set_error()}} )

    {% endif %}



    @echo off

goto:eof

:setup_build
    {{ start_section('setup_build') }}

    echo|set /p "noNewline=Host: "
    hostname


    :: Make BUILD_ENV_PATH an absolute path
    set "BUILD_ENV_PATH=%WORKING_DIR%\env"

    echo [Setting engine]

    echo conda clean -pt ^> NUL
    conda clean -pt > NUL

    echo conda-clean-build-dir
    conda-clean-build-dir

    echo conda clean --lock
    conda clean --lock


    set "CONDARC=%WORKING_DIR%\condarc"

    :: Touch file
    touch "%CONDARC%"
    {% for install_channel in install_channels -%}
    conda config --file "%CONDARC%" --add channels {{install_channel}}
    {% endfor %}
    conda config --file "%CONDARC%" --set binstar_upload no --set always_yes yes --set show_channel_urls yes

    echo "set BINSTAR_CONFIG_DIR=%WORKING_DIR%\binstar"
    set "BINSTAR_CONFIG_DIR=%WORKING_DIR%\binstar"
    echo "mkdir %BINSTAR_CONFIG_DIR%"
    mkdir "%BINSTAR_CONFIG_DIR%"
    echo "anaconda config --set url %BINSTAR_API_SITE%"
    anaconda config --set url "%BINSTAR_API_SITE%"

    call:bb_before_environment
    {{check_result()}}

    echo Rmdir /s /q "%BUILD_ENV_PATH%"
    Rmdir /s /q "%BUILD_ENV_PATH%"
    echo conda create -p "%BUILD_ENV_PATH%" --quiet --yes %BINSTAR_ENGINE%
    call conda create -p "%BUILD_ENV_PATH%" --quiet --yes %BINSTAR_ENGINE% || ( {{set_error()}} )

    echo activate %BUILD_ENV_PATH%

    :: activate does not work with paths
    :: call activate %BUILD_ENV_PATH%
    set "DEACTIVATE_PATH=%PATH%"
    set "DEACTIVATE_ENV=%CONDA_DEFAULT_ENV%"

    set "CONDA_DEFAULT_ENV=%BUILD_ENV_PATH%"
    set "PATH=%BUILD_ENV_PATH%;%BUILD_ENV_PATH%\Scripts;%PATH%"

    echo where conda
    where conda

    if "%CONDA_PY%" == "" (
        :: Hack to build with the python set in BINSTAR_ENGINE
        python -c "import sys; sys.stdout.write('{0}{1}'.format(sys.version_info[0], sys.version_info[1]))" > %TEMP%\CONDA_PY
        set /p CONDA_PY=<%TEMP%\CONDA_PY

    )
    set HAS_NUMPY=0 & conda list | findstr numpy && set HAS_NUMPY=1
    if "%HAS_NUMPY%" == "1" (
         python -c "import sys;import numpy;sys.stdout.write(''.join(numpy.__version__.split('.')[:2]))"  > %TEMP%\CONDA_NPY
         set /p CONDA_NPY=<%TEMP%\CONDA_NPY
    )

    echo CONDARC=%CONDARC%
    echo CONDA_PY=%CONDA_PY%
    echo CONDA_NPY=%CONDA_NPY%


goto:eof

:: #### #### #### #### #### #### #### #### #### #### #### #### #### ####
:: User defined build commands
:: #### #### #### #### #### #### #### #### #### #### #### #### #### ####
{% macro format_instructions(key, fail_type='error') -%}

:bb_{{key}}
    @echo off
    {% set all_instruction_lines = get_list(instructions, key) -%}
    {%- if not all_instruction_lines %}
    :: Empty set of instructions for {{key}}
    {% else -%}

    {{ start_section(key) }}

    {%   for instruction_lines in all_instruction_lines -%}
    echo {{metadata(command=instruction_lines)}}

    {%      for instruction_line in instruction_lines.split('\n') %}
    echo {{instruction_line}}
    {%      endfor %}

    ( {{instruction_lines}} ) || ( {{set_error(fail_type)}} )

    echo {{metadata(command=None)}}
    {%   endfor -%}

    @echo off

    {%- endif %}

goto:eof

{% endmacro %}

{{ format_instructions('before_environment') }}

{{ format_instructions('install') }}
{{ format_instructions('test', 'failure') }}
{{ format_instructions('before_script') }}
{{ format_instructions('script', 'failure') }}

{{ format_instructions('after_success') }}
{{ format_instructions('after_error') }}
{{ format_instructions('after_failure') }}
{{ format_instructions('after_script') }}

:binstar_build

    call:bb_install
    {{check_result()}}

    call:bb_test
    {{check_result()}}

    call:bb_before_script
    {{check_result()}}

    call:bb_script
    {{check_result()}}

    set "BINSTAR_BUILD_RESULT=success"

goto:eof


:binstar_post_build

    if "%BINSTAR_BUILD_RESULT%" == "success" (
        call:bb_after_success
    )
    if "%BINSTAR_BUILD_RESULT%" == "error" (
        call:bb_after_error
    )
    if "%BINSTAR_BUILD_RESULT%" == "failure" (
        call:bb_after_failure
    )

    call:bb_after_script

goto:eof


:upload_build_targets

    :: call deactivate
    set "CONDA_DEFAULT_ENV=%DEACTIVATE_ENV%"
    set "PATH=%DEACTIVATE_PATH%"
    set "CONDARC="

    {% if instructions.get('test_results') %}
    {{ start_section('upload_test_results') }}
    {% endif %}

    {%for test_result, filename in instructions.get('test_results', {}).items() %}

    echo anaconda build -q -t %%TOKEN%% results {{test_result}} "%BINSTAR_OWNER%/%BINSTAR_PACKAGE%" "%BINSTAR_BUILD%" {{filename}}
    anaconda build -q -t "%BINSTAR_API_TOKEN%" results {{test_result}} "%BINSTAR_OWNER%/%BINSTAR_PACKAGE%" "%BINSTAR_BUILD%" {{filename}}

    {% endfor %}

    if not "%BINSTAR_BUILD_RESULT%" == "success" (
        goto:eof
    )

    {% if test_only %}

    echo.
    echo Running Build in "Test Only" mode, not uploading build targets

    {% else %}


    {{ start_section('upload_build_targets') }}

    {% for tgt in files %}
    echo anaconda -q -t %%TOKEN%% upload {{force_upload}} --user %BINSTAR_OWNER% --package %BINSTAR_PACKAGE% {{labels}} {{tgt}} --build-id %BINSTAR_BUILD_MAJOR%
    anaconda -q -t "%BINSTAR_API_TOKEN%" upload {{force_upload}} --user "%BINSTAR_OWNER%" --package "%BINSTAR_PACKAGE%" {{labels}} {{tgt}} --build-id "%BINSTAR_BUILD%" || ( {{ set_error() }} )
    {% else %}
    echo No build targets specified
    {% endfor %}
    {% endif %}


goto:eof
