class Nwcli < Formula
  desc "Network CLI Toolbox"
  homepage "https://github.com/mathwro/nwcli"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/mathwro/nwcli/releases/download/v0.2.0/nwcli_0.2.0_darwin_arm64.tar.gz"
      sha256 "4a383db3ccd3c080b7680001acd2e1e32d6474a6f1cbf1078a8d6c7630bc732a"
    end
    on_intel do
      url "https://github.com/mathwro/nwcli/releases/download/v0.2.0/nwcli_0.2.0_darwin_amd64.tar.gz"
      sha256 "16e490c6f00b8bf6223604c59e5941c15f361be94f2b089aa94ca07b37551424"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/mathwro/nwcli/releases/download/v0.2.0/nwcli_0.2.0_linux_arm64.tar.gz"
      sha256 "7403567d38f05063185caac5998bc426e421013c4a29a166fad8a29703f8f341"
    end
    on_intel do
      url "https://github.com/mathwro/nwcli/releases/download/v0.2.0/nwcli_0.2.0_linux_amd64.tar.gz"
      sha256 "497c9b933b743b8fd8f53ea90abb3791fd7e53b9310ed00b14c8cdd607e0eb7b"
    end
  end

  def install
    bin.install "nwcli"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/nwcli --version")
  end
end
