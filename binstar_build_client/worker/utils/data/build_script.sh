#!/bin/bash
set +e

export BINSTAR_BUILD_RESULT=""

#### #### #### #### #### #### #### #### #### #### #### #### #### #### 
# Binstar defined build helper functions
#### #### #### #### #### #### #### #### #### #### #### #### #### #### 

parse_options(){


    while [[ $# > 1 ]]
    do
    key="$1"
    shift

    case $key in
        --git-oauth-token)
        GIT_OAUTH_TOKEN="$1"
        shift
        ;;

        --build-tarball)
        BUILD_TARBALL="$1"
        shift
        ;;

        --api-token)
        BINSTAR_API_TOKEN="$1"
        shift
        ;;
                
        *)

        echo "Unknown option $key"
        ;;
    esac
    done
}
#### #### #### #### #### #### #### #### #### #### #### #### #### #### 
# Binstar defined build helper functions
#### #### #### #### #### #### #### #### #### #### #### #### #### #### 

# Check the exit status of the last command and return if it was an error 
bb_check_command_error='exit_status=$?; if [ "$exit_status" != "0" ]; then echo "command exited with status $exit_status"; export BINSTAR_BUILD_RESULT="error"; return 1; fi'
# Check the exit status of the last command and return if it was an error 
bb_check_command_failure='exit_status=$?; if [ "$exit_status" != "0" ]; then echo "command exited with status $exit_status"; export BINSTAR_BUILD_RESULT="failure"; return 1; fi'
# Check the state of "BINSTAR_BUILD_RESULT" and return if it is set
bb_check_result='if [ "$BINSTAR_BUILD_RESULT" != "" ]; then return 1; fi'


#### #### #### #### #### #### #### #### #### #### #### #### #### #### 
# Binstar build variables
#### #### #### #### #### #### #### #### #### #### #### #### #### #### 

{% for key, value in exports %}
export {{key}}={{value}}
{% endfor %}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### 
# User defined build commands
#### #### #### #### #### #### #### #### #### #### #### #### #### #### 
setup_build(){


    export BUILD_ENV_PATH=`pwd`"/env"
    
    echo -e "\n[Setup Build]"

    echo "Host:" `hostname`
    echo 'Setting engine'
    
    
    echo "conda-clean-build-dir"
    conda-clean-build-dir

    echo "conda clean --lock"
    conda clean --lock

    export CONDARC=`pwd`/"condarc"

    echo "export CONDARC=$CONDARC"
    touch "$CONDARC"

    conda config --file "$CONDARC" --add channels defaults
    conda config --file "$CONDARC" \
                 --set binstar_upload no \
                 --set always_yes yes \
                 --set show_channel_urls yes


    bb_before_environment;
    
    echo "conda create -p $BUILD_ENV_PATH --quiet --yes $BINSTAR_ENGINE"
    conda create -p $BUILD_ENV_PATH --quiet --yes $BINSTAR_ENGINE
        eval $bb_check_command_error
    echo "source activate $BUILD_ENV_PATH"
    source activate $BUILD_ENV_PATH
        eval $bb_check_command_error

    echo "which conda"
    which conda

    export CONDA_PY=`python -c 'import sys; sys.stdout.write("{0}{1}".format(sys.version_info[0], sys.version_info[1]))'`
    echo "CONDA_PY=$CONDA_PY"

}

fetch_build_source(){


    echo -e '\n[Fetching Build Source]'

    SOURCE_DIR=`pwd`"/source"
    echo "SOURCE_DIR=$SOURCE_DIR"

    rm -rf "$SOURCE_DIR"
    

    {% if git_info %}
        export GIT_REPO="{{git_info['full_name']}}"
        export GIT_BRANCH="{{git_info['branch']}}"
        export GIT_COMMIT="{{git_info['commit']}}"

        echo "git clone --recursive --depth=50 --branch=$GIT_BRANCH https://github.com/${GIT_REPO}.git $SOURCE_DIR"

        if [ "$GIT_OAUTH_TOKEN" == "" ]; then
            git clone --recursive --depth=50 --branch="$GIT_BRANCH" "https://github.com/${GIT_REPO}.git" "$SOURCE_DIR"
                eval $bb_check_command_error
        else
            git clone --recursive --depth=50 --branch="$GIT_BRANCH" "https://${GIT_OAUTH_TOKEN}:x-oauth-basic@github.com/${GIT_REPO}.git" "$SOURCE_DIR"
                eval $bb_check_command_error
        fi
        
        cd "$SOURCE_DIR"

        echo "git checkout --quiet $GIT_COMMIT"
        git checkout --quiet "$GIT_COMMIT"
            eval $bb_check_command_error
        # Remove the oath token or (this would be a security violation)
        git remote rm origin
            eval $bb_check_command_error

        {% if sub_dir %}
        echo "Chaning into sub directory of git repository"
        echo "cd {{sub_dir}}"
        cd "{{sub_dir}}"
        eval $bb_check_command_error
        {% endif %}


    {% else %}

        mkdir -p "$SOURCE_DIR"
        cd "$SOURCE_DIR"

        echo "ls  -al $BUILD_TARBALL"
        ls  -al "$BUILD_TARBALL"
        echo "Extracting Package"
        echo "tar jxf $BUILD_TARBALL"
        tar jxf "$BUILD_TARBALL"
        eval $bb_check_command_error

    {% endif %}


}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### 
# User defined build commands
#### #### #### #### #### #### #### #### #### #### #### #### #### #### 
{% macro format_instructions(key, fail_type='error') -%}
    {%- set all_instruction_lines = get_list(instructions, key) -%}
    {%- if not all_instruction_lines -%}
    # Empty set of instructions for {{key}}
    true;
    {%- else %}
    echo -e '\n[{{key.title().replace('_',' ')}}]'

    {%   for instruction_lines in all_instruction_lines -%}
    {%-     for iline in instruction_lines.split('\n') -%}
    echo {{quote(iline)}}
    {{iline|safe}}
        eval $bb_check_command_{{fail_type}}

    {%     endfor -%}
    {%   endfor -%}
    {%- endif -%}
{%- endmacro %}

bb_before_environment() {
    {{format_instructions('before_environment')}}
}

bb_install() {
    {{format_instructions('install')}}
}

bb_before_script() {
    {{format_instructions('before_script')}}
}

bb_test() {
    {{format_instructions('test', fail_type='failure')}}
}

bb_script() {
    {{format_instructions('script', fail_type='failure')}}
}

bb_after_failure() {
    {{format_instructions('after_failure')}}
}

bb_after_error() {
    {{format_instructions('after_error')}}
}

bb_after_success() {
    {{format_instructions('after_success')}}
}

bb_after_script() {
    {{format_instructions('after_script')}}
    
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### 
# Assemble build commands
#### #### #### #### #### #### #### #### #### #### #### #### #### #### 

binstar_build(){

    bb_install; eval $bb_check_result
    bb_test; eval $bb_check_result
    bb_before_script; eval $bb_check_result
    bb_script; eval $bb_check_result

    export BINSTAR_BUILD_RESULT="success"

}

binstar_post_build(){
    
    if [ "$BINSTAR_BUILD_RESULT" == "success" ]; then 
        bb_after_success;
    elif [ "$BINSTAR_BUILD_RESULT" == "error" ]; then 
        bb_after_error;
    elif [ "$BINSTAR_BUILD_RESULT" == "failure" ]; then 
        bb_after_failure;
    fi

    bb_after_script;


}

upload_build_targets(){
    if [ "$BINSTAR_BUILD_RESULT" != "success" ]; then    
        return 1;
    fi
    {% if test_only %}
    echo -e '\nRunning Build in "Test Only" mode, not uploading build targets'
    {% else %}
    
    unset CONDARC
    source deactivate

    echo -e '\n[Build Targets]'
    eval $bb_check_command_error
    {% for tgt in files %}
    echo "binstar -q -t \$TOKEN upload --force --user $BINSTAR_OWNER --package $BINSTAR_PACKAGE {{channels}} {{tgt}} --build-id $BINSTAR_BUILD_MAJOR"
    
    binstar -q -t "$BINSTAR_API_TOKEN" upload --force --user "$BINSTAR_OWNER" --package "$BINSTAR_PACKAGE" {{channels}} {{tgt}} --build-id "$BINSTAR_BUILD"
    eval $bb_check_command_error
    {% else %}
    echo "No build targets specified"
    {% endfor %}
    {% endif %}

}

main(){
        
    {% if ignore_setup_build %}
    echo "[Ignore Setup Build]"
    {% else %}
    setup_build;
    {% endif %}


    if [ "$BINSTAR_BUILD_RESULT" != "" ]; then 
        echo "Internal binstar build error: Could not set up initial build state"
        exit {{EXIT_CODE_ERROR}}
    fi

    {% if ignore_fetch_build_source %}
    echo "[Ignore Fetch Build Source]"
    {% else %}
    fetch_build_source;
    {% endif %}

    if [ "$BINSTAR_BUILD_RESULT" != "" ]; then 
        echo "Binstar build error: Could not fetch build sources"
        exit {{EXIT_CODE_ERROR}}
    fi

    binstar_build
    binstar_post_build

    upload_build_targets

    echo "Exit BINSTAR_BUILD_RESULT=$BINSTAR_BUILD_RESULT"

    if [ "$BINSTAR_BUILD_RESULT" == "success" ]; then 
        exit {{EXIT_CODE_OK}}
    elif [ "$BINSTAR_BUILD_RESULT" == "error" ]; then 
        exit {{EXIT_CODE_ERROR}}
    elif [ "$BINSTAR_BUILD_RESULT" == "failure" ]; then 
        exit {{EXIT_CODE_FAILED}}
    else
        exit {{EXIT_CODE_ERROR}}
    fi    
}

#### #### #### #### #### #### #### #### #### #### #### #### #### #### 
# Execute main funtions
#### #### #### #### #### #### #### #### #### #### #### #### #### #### 
parse_options $*;
main;

