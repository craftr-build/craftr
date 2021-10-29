> Work in progress -- some functionality laid out in this readme may not be implemented yet.

# Craftr

Craftr is a general purpose build system with an easy to use API and DSL.

## Quickstart

### C++

```py
apply "@craftr/cpp"
apply "@craftr/cpp/libraries/sfml"

cpp_application "main" {
  sources [ "main.cpp" ]
  run_cwd "."
  dependencies { compile "@craftr/cpp/libraries/sfml:sfml" }
}
```

### Java

```py
apply "@craftr/java"

java_library "lib" {
  source_directory "src"
  dependencies { compile "org.tensorflow:tensorflow:1.4.0" }
}

java_application_bundle "app" {
  source_directory "src"
  main_class "Main"
  bundle_method "merge"
  dependencies { compile ":app" }
}
```

### Python

```py
apply "@craftr/python"

python_setupfiles "my_package" !yml
  version: "1.0.0"
  typed: true
  description: "My first Python package with Craftr."
  entrypoints:
    console_scripts:
      - craftr = craftr.__main__:main
```

---

<p align="center">Copyright &copy; 2021 Niklas Rosenstein</p>
