#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <nlohmann/json.hpp>
#include <redis++/redis++.h>
#include <string>
#include <vector>
#include <stdexcept>
#include <fstream>
#include <iostream>
#include <iterator>

namespace py = pybind11;
using json = nlohmann::json;

class BeerRAGAgent {
public:
    BeerRAGAgent(const std::string& config_path, py::function generate_callback) {
        std::ifstream config_file(config_path);
        if (!config_file.is_open()) {
            throw std::runtime_error("Cannot open config.json");
        }
        config = json::parse(config_file);
        instructions = config["INSTRUCTIONS"];
        prompt_template = config["PROMPT_TEMPLATE"];
        this->generate_callback = generate_callback;
    }

    std::string retrieve_from_redis(const std::string& query) {
        try {
            sw::redis::Redis redis("tcp://localhost:6379");
            std::vector<std::string> results;
            redis.keys("beer:meta:*", std::back_inserter(results));
            std::string context = "";
            for (const auto& key : results) {
                auto value = redis.get(key);
                if (value) {
                    try {
                        json meta = json::parse(*value);
                        context += "Name: " + meta["name"].get<std::string>() + 
                                  ", Description: " + meta["description"].get<std::string>() + 
                                  ", Style: " + meta["style"].get<std::string>() + 
                                  ", ABV: " + std::to_string(meta["abv"].get<double>()) + "\n";
                    } catch (const json::exception& e) {
                        context += "Error parsing metadata for " + key + ": " + e.what() + "\n";
                    }
                }
            }
            return context.empty() ? "No beer data found." : context;
        } catch (const std::exception& e) {
            return "Error retrieving from Redis: " + std::string(e.what());
        }
    }

    std::string generate_response(const std::string& query) {
        std::string context = retrieve_from_redis(query);
        std::string prompt = prompt_template;
        prompt.replace(prompt.find("{documents}"), 11, context);
        prompt.replace(prompt.find("{query}"), 7, query);
        prompt = instructions + "\n" + prompt;

        try {
            return py::cast<std::string>(generate_callback(prompt));
        } catch (const py::error_already_set& e) {
            return "Python error: " + std::string(e.what());
        }
    }

private:
    json config;
    std::string instructions;
    std::string prompt_template;
    py::function generate_callback;
};

PYBIND11_MODULE(gemma_agent, m) {
    py::class_<BeerRAGAgent>(m, "BeerRAGAgent")
        .def(py::init<const std::string&, py::function>())
        .def("generate_response", &BeerRAGAgent::generate_response);
}