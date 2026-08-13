class Azc < Formula
  desc "Fast subscription context switcher for Azure CLI"
  homepage "https://github.com/mathwro/azc"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.1.0/azc_0.1.0_darwin_arm64.tar.gz"
      sha256 "c8a1e0d695b5b722c6184baf997270a29bb4861d2c050d68b9102adc6d761d65"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.1.0/azc_0.1.0_darwin_amd64.tar.gz"
      sha256 "cb2ab9ca3d154f69e5a0815c88b0ecd1e6a97ab1d4c8b6114c68a57a6aa7a40b"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/azc/releases/download/v0.1.0/azc_0.1.0_linux_arm64.tar.gz"
      sha256 "c93d6b8f03749243e67e142c16fb49bb90d5abad287215faac565486c1e33701"
    end
    on_intel do
      url "https://github.com/mathwro/azc/releases/download/v0.1.0/azc_0.1.0_linux_amd64.tar.gz"
      sha256 "02b431ee5cd492ee7daa8c6e8cab60c0b5d23dcf294f134f02384adc558b16ea"
    end
  end

  def install
    bin.install "azc"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/azc --version")
  end
end
